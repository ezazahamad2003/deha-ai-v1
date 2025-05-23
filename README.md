# Deha AI - Medical PDF Assistant

Deha AI is a web application that allows users to upload medical PDFs and ask questions about the content. It features both text-based chat and voice interaction capabilities using Deepgram's speech recognition and text-to-speech technology.

## Features

- Upload and process medical PDF documents
- Text-based chat interface to ask questions about the PDF content
- Voice interaction through a call feature
- Responsive design with visual feedback

## Technologies Used

- **Backend**: Flask (Python)
- **Frontend**: HTML, CSS, JavaScript
- **AI**: Google Gemini API for natural language processing
- **Speech**: Deepgram API for speech recognition and text-to-speech
- **PDF Processing**: PyPDF for text extraction

## Setup

1. Clone the repository
2. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
3. Get your Gemini API key from [Google's AI Studio](https://makersuite.google.com/app/apikey)
4. Update `.env` with your API key
5. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
6. Run the application:
   ```bash
   python app.py
   ```

## Security Notes

- Never commit your `.env` file containing API keys
- Keep your API keys secure and rotate them regularly
- Use environment variables for all sensitive configuration