document.addEventListener('DOMContentLoaded', () => {
  const chatMessages = document.querySelector('.chat-messages');
  const messageInput = document.querySelector('#message-input');
  const sendButton = document.querySelector('#send-button');
  const uploadButton = document.querySelector('#upload-button');
  const imageInput = document.querySelector('#image-input');
  const initialMessage = document.getElementById('initial-message');
  const toggleDarkModeButton = document.getElementById('toggle-dark-mode');

  let sessionId = Date.now().toString();
  let imageUploaded = false;

  function addMessage(message, isBot, isImage = false, isLoading = false) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('message');
    messageElement.classList.add(isBot ? 'bot-message' : 'user-message');
    
    const logoElement = document.createElement('div');
    logoElement.classList.add('message-logo');
    logoElement.textContent = isBot ? '🤖' : '👤'; // You can replace these with actual image URLs
    
    const contentElement = document.createElement('div');
    contentElement.classList.add('message-content');
    
    if (isImage) {
        contentElement.classList.add('image-message');
        const img = document.createElement('img');
        img.src = URL.createObjectURL(message);
        contentElement.appendChild(img);
    } else if (isLoading) {
        contentElement.classList.add('loading-message');
        contentElement.innerHTML = '<div class="loading-dots"><span>.</span><span>.</span><span>.</span></div>';
    } else {
        contentElement.innerHTML = convertToBold(message); // Use innerHTML to allow HTML content
    }

    messageElement.appendChild(logoElement);
    messageElement.appendChild(contentElement);
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return messageElement;
  }

  // Function to convert double asterisks to HTML bold tags
  function convertToBold(text) {
    // Replace double asterisks with <strong> tags
    while (text.includes('**')) {
      text = text.replace('**', '<strong>'); // Replace first instance with opening tag
      text = text.replace('**', '</strong>'); // Replace next instance with closing tag
    }
    return text;
  }

  function sendMessage() {
    const message = messageInput.value.trim();
    
    if (message) {
      addMessage(message, false);
      messageInput.value = '';
      initialMessage.style.display = 'none';
      
      const loadingMessage = addMessage('', true, false, true);
      
      fetch('/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: message,
          session_id: sessionId
        }),
      })
      .then(response => response.json())
      .then(data => {
        chatMessages.removeChild(loadingMessage);
        addMessage(data.response, true);
        if (data.end_conversation) {
          messageInput.disabled = true;
          sendButton.disabled = true;
        }
      })
      .catch(error => {
        chatMessages.removeChild(loadingMessage);
        console.error('Error:', error);
        addMessage("Sorry, something went wrong. Please try again later.", true);
      });
    }
  }

  sendButton.addEventListener('click', sendMessage);
  messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      sendMessage();
    }
  });

  uploadButton.addEventListener('click', () => {
    imageInput.click();
  });

  imageInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file && file.type.startsWith('image/')) {
      addMessage(file, false, true);  // Display the uploaded image immediately
      const loadingMessage = addMessage('', true, false, true);  // Show loading dots

      const formData = new FormData();
      formData.append('image', file);
      formData.append('session_id', sessionId);

      fetch('/upload', {
        method: 'POST',
        body: formData,
      })
      .then(response => response.json())
      .then(data => {
        chatMessages.removeChild(loadingMessage);  // Remove loading indicator
        addMessage(data.analysis, true);  // Show analysis result
        initialMessage.style.display = 'none';
      })
      .catch(error => {
        chatMessages.removeChild(loadingMessage);
        console.error('Error:', error);
        addMessage("Sorry, there was an error uploading the image. Please try again.", true);
      });
    } else {
      addMessage("Please upload a valid image file.", true);
    }
  });

  toggleDarkModeButton.addEventListener('click', () => {
    document.body.classList.toggle('dark-mode');
  });

  messageInput.addEventListener('input', () => {
    initialMessage.style.display = 'none';
  });
});
