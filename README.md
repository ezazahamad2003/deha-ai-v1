# Deha AI - Medical Information System

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