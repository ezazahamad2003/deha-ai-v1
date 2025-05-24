import os
from flask import Flask, render_template, request, jsonify, session
from werkzeug.utils import secure_filename
import io
import flask
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from dotenv import load_dotenv
import google.generativeai as genai
from pypdf import PdfReader
from audio import speak, listen  # Import the audio functions

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__, static_folder='static')
app.secret_key = os.urandom(24) # Needed for session management

# --- Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set. Please set it before running.")
genai.configure(api_key=GEMINI_API_KEY)

GEMINI_MODEL_NAME = "gemini-1.5-flash-latest" # Or your preferred model

# --- Load System Prompt from File ---
def load_system_prompt(file_path: str) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        # Try to find it relative to the script's directory if path is relative
        script_dir = os.path.dirname(os.path.abspath(__file__))
        abs_file_path = os.path.join(script_dir, file_path)
        try:
            with open(abs_file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"System prompt file not found at: {file_path} or {abs_file_path}")
    except Exception as e:
        raise IOError(f"Error reading system prompt file: {e}")

try:
    SYSTEM_PROMPT_CONTENT = load_system_prompt("system_prompt.txt")
except Exception as e:
    print(f"FATAL ERROR: Could not load system prompt. {e}")
    # In a web app, you might want to handle this more gracefully,
    # but for now, exiting or raising is fine for startup.
    raise

# --- PDF Text Extraction Function ---
def extract_text_from_pdf(pdf_input):
    """Extract text from a PDF file path or bytes."""
    text = ""
    try:
        from pypdf import PdfReader
        import io
        # Handle both file paths and bytes
        if isinstance(pdf_input, bytes):
            pdf_file = io.BytesIO(pdf_input)
            reader = PdfReader(pdf_file)
        else:  # Assume it's a file path
            reader = PdfReader(pdf_input)
        for page in reader.pages:
            extracted_text = page.extract_text()
            if extracted_text:
                text += extracted_text + "\n"
        return text
    except Exception as e:
        app.logger.error(f"Error extracting text from PDF: {e}")
        return ""

# --- Deha AI Backend Logic for Web ---
def deha_ai_web_backend(patient_pdf_content: str, patient_question: str, chat_history: list) -> tuple[str, list]:
    if not patient_pdf_content.strip():
        return "Error: PDF content is missing or empty.", chat_history

    initial_context_message = f"""
    {SYSTEM_PROMPT_CONTENT}

    Here is the extracted text from the patient's medical PDF:
    <PDF_START>
    {patient_pdf_content}
    <PDF_END>
    """

    try:
        model = genai.GenerativeModel(GEMINI_MODEL_NAME)
        
        # Convert chat history to a format that can be serialized for session storage
        serializable_history = []
        if chat_history:
            for msg in chat_history:
                if hasattr(msg, 'role') and hasattr(msg, 'parts'):
                    parts_text = [part.text if hasattr(part, 'text') else str(part) for part in msg.parts]
                    serializable_history.append({
                        'role': msg.role,
                        'parts': parts_text
                    })
                elif isinstance(msg, dict) and 'role' in msg and 'parts' in msg:
                    serializable_history.append(msg)
        
        # Start a new chat or continue existing one
        if not serializable_history:
            # First interaction - send system prompt and PDF content
            chat = model.start_chat(history=[
                {"role": "user", "parts": [initial_context_message]}
            ])
        else:
            # Continue existing chat
            chat = model.start_chat(history=serializable_history)
        
        # Send the user's question
        response = chat.send_message(
            content=patient_question,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7, top_p=0.95, top_k=40, max_output_tokens=1024
            )
        )
        
        # Get the AI's answer text
        ai_answer = response.text
        
        # Get updated history and convert to serializable format
        updated_history = chat.history
        serializable_updated_history = []
        for msg in updated_history:
            if hasattr(msg, 'role') and hasattr(msg, 'parts'):
                parts_text = [part.text if hasattr(part, 'text') else str(part) for part in msg.parts]
                serializable_updated_history.append({
                    'role': msg.role,
                    'parts': parts_text
                })
        
        return ai_answer, serializable_updated_history
    except Exception as e:
        app.logger.error(f"Error in deha_ai_web_backend: {str(e)}")
        return f"I apologize, but an error occurred: {str(e)}", chat_history

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'pdf_file' not in request.files:
            flask.flash('No file part')
            return redirect(request.url)
        file = request.files['pdf_file']
        if file.filename == '':
            flask.flash('No selected file')
            return redirect(request.url)
        if file and file.filename.endswith('.pdf'):
            try:
                pdf_bytes = file.read()
                extracted_text = extract_text_from_pdf(pdf_bytes)
                if not extracted_text.strip():
                    flask.flash('Could not extract text from PDF. Please ensure it has selectable text.')
                    session.pop('patient_pdf_content', None)
                    session.pop('chat_history', None)
                else:
                    session['patient_pdf_content'] = extracted_text
                    session['chat_history'] = [] # Initialize chat history
                    flask.flash('PDF processed successfully! You can now ask questions.')
                return redirect(url_for('index'))
            except Exception as e:
                app.logger.error(f"Error processing PDF: {e}")
                flask.flash(f'Error processing PDF: {e}')
                return redirect(request.url)
        else:
            flask.flash('Invalid file type. Please upload a PDF.')
            return redirect(request.url)

    # For GET request, or after POST redirect
    patient_pdf_content = session.get('patient_pdf_content')
    chat_history_display = session.get('chat_history', [])
    
    # Format chat history for display (user/model distinction)
    display_messages = []
    if chat_history_display:
        # The first "user" message in history is the system prompt + PDF, skip for display
        # Actual Q&A starts from the second user message if the first one was context
        # However, gemini history stores user question then model answer.
        # The initial context message is not directly part of the Q&A display.
        # We need to filter out the very first "user" part if it's just the context.
        # For simplicity, we'll display all turns. The user will see their question and the AI's answer.
        
        # The history from Gemini is a list of Content objects.
        # Each Content object has a role ('user' or 'model') and parts.
        temp_history = list(chat_history_display) # Make a copy

        # Remove the initial context message if it's the first user message and contains SYSTEM_PROMPT_CONTENT
        if temp_history and temp_history[0]['role'] == 'user' and SYSTEM_PROMPT_CONTENT in temp_history[0]['parts'][0]:
            # This was our initial context message, don't display it as a "user question"
            # The actual Q&A starts after this.
            # However, the model's response to this is also not relevant.
            # This logic needs refinement based on how `start_chat` and `send_message` structure history.
            # For now, let's assume chat_history in session stores Q&A pairs.
            pass # We will handle this in the template or JS for cleaner display

    return render_template('index.html', pdf_processed=bool(patient_pdf_content), chat_history=chat_history_display)

@app.route('/ask', methods=['POST'])
def ask():
    data = request.get_json()
    patient_question = data.get('question')

    if not patient_question:
        return jsonify({"error": "No question provided"}), 400

    patient_pdf_content = session.get('patient_pdf_content')
    if not patient_pdf_content:
        return jsonify({"error": "PDF not processed or session expired. Please upload PDF again."}), 400

    chat_history = session.get('chat_history', [])
    
    try:
        answer, updated_chat_history = deha_ai_web_backend(patient_pdf_content, patient_question, chat_history)
        
        # Store the updated chat history in the session
        session['chat_history'] = updated_chat_history
        
        # Return just the answer text
        return jsonify({"answer": answer})
    except Exception as e:
        app.logger.error(f"Error in ask route: {str(e)}")
        return jsonify({"error": f"Server error: {str(e)}"}), 500

@app.route('/reset', methods=['GET'])
def reset_session():
    session.pop('patient_pdf_content', None)
    session.pop('chat_history', None)
    flask.flash('Session reset. Please upload a new PDF.')
    return redirect(url_for('index'))

# Add this import at the top of your file
from audio import speak, listen, set_stop_audio

# Then update your call endpoint
@app.route('/call', methods=['POST'])
def call():
    """Handle voice call requests"""
    data = request.get_json()
    action = data.get('action')
    
    if action == 'start':
        # Initialize call session
        session['call_active'] = True
        return jsonify({"status": "Call started"})
    
    elif action == 'end':
        # End call session
        session.pop('call_active', None)
        # Stop any ongoing audio operations
        set_stop_audio(True)
        return jsonify({"status": "Call ended"})
    
    elif action == 'speak':
        # Process speech from user
        patient_pdf_content = session.get('patient_pdf_content')
        if not patient_pdf_content:
            return jsonify({"error": "PDF not processed or session expired"}), 400
        
        # Get the transcribed text from the request
        transcribed_text = data.get('text')
        if not transcribed_text:
            return jsonify({"error": "No speech text provided"}), 400
        
        chat_history = session.get('chat_history', [])
        
        # Process with AI
        answer, updated_chat_history = deha_ai_web_backend(patient_pdf_content, transcribed_text, chat_history)
        
        # Update session
        session['chat_history'] = updated_chat_history
        
        # Use the Deepgram speak function to generate speech
        # This will be handled by a separate endpoint
        
        return jsonify({
            "question": transcribed_text,
            "answer": answer
        })
    
    elif action == 'listen':
        # Use the listen function from audio.py to capture speech
        try:
            transcribed_text = listen()
            if transcribed_text:
                return jsonify({"text": transcribed_text})
            else:
                return jsonify({"error": "No speech detected"}), 400
        except Exception as e:
            app.logger.error(f"Error in listen: {str(e)}")
            return jsonify({"error": f"Error capturing speech: {str(e)}"}), 500
    
    return jsonify({"error": "Invalid action"}), 400

# Add a new endpoint to handle text-to-speech using Deepgram
@app.route('/speak', methods=['POST'])
def text_to_speech():
    """Convert text to speech using Deepgram"""
    data = request.get_json()
    text = data.get('text')
    
    if not text:
        return jsonify({"error": "No text provided"}), 400
    
    try:
        # Use the speak function from audio.py
        speak(text)
        return jsonify({"status": "Speech generated successfully"})
    except Exception as e:
        app.logger.error(f"Error in text_to_speech: {str(e)}")
        return jsonify({"error": f"Error generating speech: {str(e)}"}), 500

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({"response": "Please provide a message"}), 400
    
    # Get PDF text from session - use patient_pdf_content to match the rest of your code
    patient_pdf_content = session.get('patient_pdf_content', '')
    
    if not patient_pdf_content:
        return jsonify({"response": "Please upload a PDF document first"}), 400
    
    # Process the message with your AI model
    try:
        # Call your Gemini API
        response = process_with_gemini(user_message, patient_pdf_content)
        return jsonify({"response": response}), 200
    except Exception as e:
        return jsonify({"response": f"Error: {str(e)}"}), 500

def process_with_gemini(question, context):
    """Process a question with Google's Gemini API."""
    # Import your Gemini processing code here
    import google.generativeai as genai
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    
    # Configure the API key
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    
    # Set up the model - use the same model as defined at the top of the file
    model = genai.GenerativeModel(GEMINI_MODEL_NAME)  # Use GEMINI_MODEL_NAME instead of hardcoded 'gemini-pro'
    
    # Create a prompt with the context and question
    prompt = f"""
    Context information is below.
    ---------------------
    {context}
    ---------------------
    Given the context information and not prior knowledge, answer the question: {question}
    """
    
    # Generate a response
    response = model.generate_content(prompt)
    
    return response.text

# Add this route to handle file uploads
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'pdfFile' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['pdfFile']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and file.filename.endswith('.pdf'):
        try:
            # Read the file bytes
            pdf_bytes = file.read()

            # Extract text directly from bytes
            pdf_text = extract_text_from_pdf(pdf_bytes)

            if not pdf_text.strip():
                return jsonify({"error": "Could not extract text from PDF"}), 400

            # Store in session for later use
            session['patient_pdf_content'] = pdf_text
            session['pdf_filename'] = file.filename
            session['chat_history'] = []  # Initialize chat history

            return jsonify({"success": True, "filename": file.filename}), 200
        except Exception as e:
            app.logger.error(f"Error processing PDF: {e}")
            return jsonify({"error": str(e)}), 500
    else:
        return jsonify({"error": "File must be a PDF"}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5001) # Use a different port if 5000 is in use