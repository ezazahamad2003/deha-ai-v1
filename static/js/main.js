document.addEventListener('DOMContentLoaded', function() {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('pdfFile');
    const uploadedFileName = document.getElementById('uploadedFileName');
    const userInput = document.getElementById('userInput');
    const sendButton = document.getElementById('sendButton');
    const chatMessages = document.getElementById('chatMessages');
    
    // Dropzone functionality
    if (dropzone) {
        // Handle file selection via button
        fileInput.addEventListener('change', function(e) {
            if (fileInput.files.length > 0) {
                handleFileUpload(fileInput.files[0]);
            }
        });
        
        // Handle drag and drop
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropzone.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropzone.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropzone.addEventListener(eventName, unhighlight, false);
        });
        
        function highlight() {
            dropzone.classList.add('dragover');
        }
        
        function unhighlight() {
            dropzone.classList.remove('dragover');
        }
        
        dropzone.addEventListener('drop', handleDrop, false);
        
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            
            if (files.length > 0) {
                handleFileUpload(files[0]);
            }
        }
    }
    
    // File upload handling
    function handleFileUpload(file) {
        if (file.type !== 'application/pdf') {
            alert('Please upload a PDF file');
            return;
        }
        
        // Show uploading state
        dropzone.classList.add('uploading');
        
        const formData = new FormData();
        formData.append('pdfFile', file);
        
        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Show success state
            dropzone.classList.remove('uploading');
            dropzone.classList.add('success');
            uploadedFileName.textContent = file.name;
            
            // Add welcome message
            appendMessage('Deha AI', 'PDF uploaded successfully! How can I help you with this document?', false);
        })
        .catch(error => {
            console.error('Error:', error);
            dropzone.classList.remove('uploading');
            alert('Error uploading file: ' + error.message);
        });
    }
    
    // Chat functionality
    if (sendButton && userInput) {
        sendButton.addEventListener('click', sendMessage);
        userInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });
    }
    
    function sendMessage() {
        const message = userInput.value.trim();
        if (message === '') return;
        
        // Add user message to chat
        appendMessage('You', message, true);
        userInput.value = '';
        
        // Send message to server
        fetch('/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ question: message }),
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Server responded with ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('Response data:', data); // Debug log
            // Add AI response to chat
            if (data.answer) {
                appendMessage('Deha AI', data.answer, false);
            } else if (data.error) {
                appendMessage('Deha AI', `Error: ${data.error}`, false);
            } else {
                appendMessage('Deha AI', 'Sorry, I received an empty response.', false);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            appendMessage('Deha AI', `Sorry, there was an error: ${error.message}`, false);
        });
    }
    
    function appendMessage(sender, text, isUser) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        messageDiv.classList.add(isUser ? 'user-message' : 'ai-message');
        
        const senderStrong = document.createElement('strong');
        senderStrong.textContent = sender + ': ';
        messageDiv.appendChild(senderStrong);
        
        const messageText = document.createTextNode(text);
        messageDiv.appendChild(messageText);
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
});