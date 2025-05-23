document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chatForm');
    const chatBox = document.getElementById('chatBox');
    const questionInput = document.getElementById('question');
    const loader = document.getElementById('loader');

    if (chatForm) {
        chatForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            const userQuestion = questionInput.value.trim();
            if (!userQuestion) return;

            appendMessage('You', userQuestion, true);
            questionInput.value = '';
            loader.style.display = 'block'; // Show loader

            try {
                const response = await fetch("/ask", {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ question: userQuestion }),
                });

                loader.style.display = 'none'; // Hide loader

                if (!response.ok) {
                    const errorData = await response.json();
                    appendMessage('Error', errorData.error || 'Failed to get response from server.', false);
                    return;
                }

                const data = await response.json();
                appendMessage('Deha AI', data.answer, false);

            } catch (error) {
                loader.style.display = 'none'; // Hide loader
                console.error('Error:', error);
                appendMessage('Error', 'Could not connect to the server or an error occurred.', false);
            }
        });
    }

    function appendMessage(sender, text, isUser) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message');
        messageDiv.classList.add(isUser ? 'user-message' : 'ai-message');
        
        const senderStrong = document.createElement('strong');
        senderStrong.textContent = sender + ': ';
        messageDiv.appendChild(senderStrong);
        
        // Handle newlines in AI responses
        const messageText = document.createTextNode(text);
        messageDiv.appendChild(messageText);
        
        chatBox.appendChild(messageDiv);
        chatBox.scrollTop = chatBox.scrollHeight; // Auto-scroll to bottom
    }
    
    // Scroll chat to bottom on page load if there's history
    if (chatBox) {
        chatBox.scrollTop = chatBox.scrollHeight;
    }
});