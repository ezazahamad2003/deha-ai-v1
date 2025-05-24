document.addEventListener('DOMContentLoaded', function() {
    const startCallButton = document.getElementById('startCallButton');
    const callInterface = document.getElementById('callInterface');
    const endCallButton = document.getElementById('endCallButton');
    const callStatus = document.getElementById('callStatus');
    const audioLevel = document.getElementById('audioLevel');
    const chatBox = document.getElementById('chatBox');
    
    let isCallActive = false;
    
    if (startCallButton) {
        startCallButton.addEventListener('click', startCall);
    }
    
    if (endCallButton) {
        endCallButton.addEventListener('click', endCall);
    }
    
    async function startCall() {
        try {
            // Start call on server
            const response = await fetch('/call', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ action: 'start' }),
            });
            
            if (!response.ok) {
                throw new Error('Failed to start call');
            }
            
            // Show call interface
            callInterface.style.display = 'block';
            isCallActive = true;
            
            // Start the conversation loop
            startConversation();
            
        } catch (error) {
            console.error('Error starting call:', error);
            callStatus.textContent = "Error starting call";
            setTimeout(() => {
                callInterface.style.display = 'none';
            }, 3000);
        }
    }
    
    async function endCall() {
        isCallActive = false;
        callInterface.style.display = 'none';
        
        try {
            // End call on server
            await fetch('/call', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ action: 'end' }),
            });
        } catch (error) {
            console.error('Error ending call:', error);
        }
        
        // Stop audio visualization
        stopAudioVisualization();
    }
    
    async function startConversation() {
        if (!isCallActive) return;
        
        try {
            // Start listening
            callStatus.textContent = "Listening...";
            startAudioVisualization();
            
            // Call the server to listen for speech
            const listenResponse = await fetch('/call', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ action: 'listen' }),
            });
            
            if (!listenResponse.ok) {
                const errorData = await listenResponse.json();
                throw new Error(errorData.error || 'Failed to capture speech');
            }
            
            const listenData = await listenResponse.json();
            
            if (!listenData.text) {
                // If no speech was detected, start listening again
                setTimeout(() => {
                    if (isCallActive) startConversation();
                }, 1000);
                return;
            }
            
            // Process the transcribed text
            callStatus.textContent = "Processing...";
            
            // Send the transcribed text to the server
            const speakResponse = await fetch('/call', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    action: 'speak',
                    text: listenData.text 
                }),
            });
            
            if (!speakResponse.ok) {
                const errorData = await speakResponse.json();
                throw new Error(errorData.error || 'Failed to process speech');
            }
            
            const speakData = await speakResponse.json();
            
            // Add to chat history
            appendMessage('You', speakData.question, true);
            appendMessage('Deha AI', speakData.answer, false);
            
            // Generate speech for the AI's response
            callStatus.textContent = "Speaking...";
            
            // Call the server to generate speech
            const ttsResponse = await fetch('/speak', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ text: speakData.answer }),
            });
            
            if (!ttsResponse.ok) {
                const errorData = await ttsResponse.json();
                throw new Error(errorData.error || 'Failed to generate speech');
            }
            
            // CHANGE: Reduce the wait time after speech
            // Instead of using a fixed time based on text length, use a smaller fixed delay
            await new Promise(resolve => setTimeout(resolve, 500)); // Just 500ms delay
            
            // Start the next conversation turn if the call is still active
            if (isCallActive) {
                startConversation();
            }
            
        } catch (error) {
            console.error('Error in conversation:', error);
            callStatus.textContent = "Error: " + error.message;
            
            // Try to restart the conversation after a delay
            setTimeout(() => {
                if (isCallActive) startConversation();
            }, 3000);
        }
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
        
        chatBox.appendChild(messageDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    }
    
    let audioVisualizationInterval = null;
    
    function startAudioVisualization() {
        audioVisualizationInterval = setInterval(() => {
            const level = Math.random() * 100;
            audioLevel.style.width = level + '%';
        }, 100);
    }
    
    function stopAudioVisualization() {
        if (audioVisualizationInterval) {
            clearInterval(audioVisualizationInterval);
            audioVisualizationInterval = null;
        }
    }
});