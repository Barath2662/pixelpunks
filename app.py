from flask import Flask, request, jsonify, render_template
import google.generativeai as genai
from PIL import Image
import io
import concurrent.futures
import logging

app = Flask(__name__)

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG)

# Configure the Gemini API with your API key
genai.configure(api_key="AIzaSyALoj2MO68_4KFq-TJ2Pyx7VPxxS1JG7nE")

# Initialize the Gemini models
flash_model = genai.GenerativeModel('gemini-1.5-flash')
pro_model = genai.GenerativeModel('gemini-1.5-pro')

# Store conversation history
conversation_history = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image file uploaded'}), 400

    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({'error': 'No image selected'}), 400

    try:
        # Read the image file
        image_bytes = image_file.read()
        image = Image.open(io.BytesIO(image_bytes))

        # Initial prompt to analyze the image
        initial_prompt = "Analyze this image in detail. Note down what you see, including objects, colors, and any notable features. Describe the image in 2 lines."

        # Get initial analysis from Gemini Flash
        response = flash_model.generate_content([initial_prompt, image])
        analysis = response.text

        # Store the analysis in conversation history and mark image as uploaded
        session_id = request.form.get('session_id')
        conversation_history[session_id] = {
            'image_analysis': analysis,
            'image_uploaded': True,  # Mark that an image was uploaded
            'chat_history': f"Image analysis: {analysis}\n\n"
        }

        return jsonify({'analysis': analysis})
    except Exception as e:
        logging.error(f"Error during image upload: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_input = data.get('message')
    session_id = data.get('session_id')

    if not user_input or not session_id:
        return jsonify({'error': 'Invalid request'}), 400

    # Check for exit commands
    exit_commands = ["quit", "bye", "thank you", "exit"]
    if any(cmd in user_input.lower() for cmd in exit_commands):
        return jsonify({
            'response': "Thank you for chatting with me. I hope you found our conversation helpful. Goodbye!",
            'end_conversation': True
        })

    try:
        session_data = conversation_history.get(session_id, {})
        chat_history = session_data.get('chat_history', '')
        image_uploaded = session_data.get('image_uploaded', False)  # Check if image was uploaded
        image_analysis = session_data.get('image_analysis', '')

        # Handle image-related questions if an image is uploaded
        if image_uploaded and is_image_related(user_input, image_analysis):
            # Use Gemini Flash model for image-related responses
            prompt = f"{chat_history}Human: {user_input}\n"
            response = flash_model.generate_content(prompt)
            bot_response = response.text.strip()
        elif not image_uploaded and is_image_related(user_input, ''):
            # If the question is image-related but no image has been uploaded
            bot_response = "You did not provide an image for me to analyze. Please upload an image or provide a link."
        else:
            # Use the Pro model for general conversation (greetings, small talk, etc.)
            prompt = f"{chat_history}Human: {user_input}\n"
            bot_response = get_response_with_timeout(prompt).strip()

        # Convert double asterisks to HTML <strong> tags
        bot_response = convert_to_bold(bot_response)

        # Update conversation history
        if session_id not in conversation_history:
            conversation_history[session_id] = {'chat_history': ''}
        conversation_history[session_id]['chat_history'] += f"Human: {user_input}\nAI: {bot_response}\n"

        return jsonify({'response': bot_response})
    except Exception as e:
        logging.error(f"Error during chat: {e}")
        return jsonify({'error': str(e)}), 500


# Helper function to get response with timeout
def get_response_with_timeout(prompt, timeout=10):
    def get_pro_response():
        return pro_model.generate_content(prompt).text

    def get_flash_response():
        return flash_model.generate_content(prompt).text

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(get_pro_response)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            logging.warning("Pro model timed out, falling back to Flash model")
            # If Gemini Pro times out, use Gemini Flash instead
            return get_flash_response()

# Function to convert double asterisks to HTML bold tags
def convert_to_bold(text):
    # Replace double asterisks with <strong> tags
    while '**' in text:
        text = text.replace('**', '<strong>', 1)  # Replace first instance with opening tag
        text = text.replace('**', '</strong>', 1)  # Replace next instance with closing tag
    return text

# Function to check if the user input is related to the image analysis
def is_image_related(user_input, image_analysis):
    image_keywords = set(image_analysis.lower().split())
    question_keywords = set(user_input.lower().split())

    # Check if there's any overlap between question keywords and image keywords
    if len(image_keywords.intersection(question_keywords)) > 0:
        return True

    # Check for image-related phrases
    image_phrases = ["in the image", "in the picture", "what do you see", "describe the", "is there any text"]
    if any(phrase in user_input.lower() for phrase in image_phrases):
        return True

    return False

if __name__ == '__main__':
    app.run(debug=True)
