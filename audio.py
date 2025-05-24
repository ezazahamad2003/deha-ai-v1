#this is a deepgram tts 

# audio.py

import os
import pyaudio
import wave
import tempfile
import pyttsx3
from deepgram import DeepgramClient, FileSource, PrerecordedOptions, SpeakOptions
import numpy as np
from collections import deque
import webrtcvad
import time
import speech_recognition as sr
import simpleaudio as sa
import pygame
from PyQt5.QtCore import QThread, pyqtSignal
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration and Initialization ---

# Get Deepgram API key from environment variable
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
if not DEEPGRAM_API_KEY:
    raise ValueError("DEEPGRAM_API_KEY environment variable not set. Please set it in your .env file.")

deepgram = DeepgramClient(DEEPGRAM_API_KEY)
filename = "test.mp3"
# Initialize the text-to-speech engine
engine = pyttsx3.init()

# --- Text-to-Speech Function ---

# Add a global variable to track if we should stop audio operations
_should_stop_audio = False

def set_stop_audio(should_stop=True):
    """
    Sets the flag to stop audio operations.
    """
    global _should_stop_audio
    _should_stop_audio = should_stop

def speak(text):
    try:
        global _should_stop_audio
        _should_stop_audio = False
        
        # STEP 1: Initialize Deepgram Client
        deepgram = DeepgramClient(api_key=DEEPGRAM_API_KEY)
        SPEAK_TEXT = {"text": text}
        # STEP 2: Define TTS options
        options = SpeakOptions(
            model="aura-luna-en",  # Specify the Deepgram voice model
        )

        # STEP 3: Call the save method with correct arguments
        response = deepgram.speak.rest.v("1").save(filename, SPEAK_TEXT, options)

        print(f"✅ Speech saved as {filename}")

        # STEP 4: Play the generated speech file
        play_mp3(filename)
        
        # Add a small delay to ensure everything is complete
        time.sleep(0.5)

    except Exception as e:
        print(f"🚨 Exception: {e}")

def play_mp3(file_path):
    """
    Plays an MP3 file using pygame.
    """
    try:
        global _should_stop_audio
        
        pygame.init()
        pygame.mixer.init()
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        
        # Wait for playback to complete or until stop is requested
        while pygame.mixer.music.get_busy() and not _should_stop_audio:
            pygame.time.Clock().tick(10)
        
        # If we're stopping due to a request, stop the playback
        if _should_stop_audio:
            pygame.mixer.music.stop()
            print("🛑 Audio playback stopped by request.")
        else:
            print("🔊 Audio playback complete.")
            
        pygame.mixer.music.unload()
        
    except Exception as e:
        print(f"🚨 Error playing MP3: {e}")

def record_audio(samplerate=16000, channels=1, chunk=320, silence_duration=1.5):
    """
    Records audio from the microphone and stops when silence is detected.

    Parameters:
      - samplerate: The sample rate for recording (must be 8000, 16000, 32000, or 48000).
      - channels: Number of audio channels (must be 1 for VAD).
      - chunk: The number of frames per buffer (must align with 10ms audio length for VAD).
      - silence_duration: Time (in seconds) of silence required to stop recording.

    Returns:
      The filename of the recorded WAV file.
    """
    global _should_stop_audio
    _should_stop_audio = False
    
    print("🎤 Listening... Speak now!")

    # Initialize PyAudio
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16,
                    channels=channels,
                    rate=samplerate,
                    input=True,
                    frames_per_buffer=chunk)

    # Initialize WebRTC VAD
    vad = webrtcvad.Vad()
    vad.set_mode(3)  # Most aggressive mode for speech detection

    frames = []
    silence_count = 0
    silence_threshold = int(silence_duration * samplerate / chunk)  # Convert silence time to chunks

    while not _should_stop_audio:
        data = stream.read(chunk, exception_on_overflow=False)
        frames.append(data)
        
        # Convert audio to PCM16 little-endian format
        pcm_data = np.frombuffer(data, dtype=np.int16)

        # Check VAD only if chunk size aligns with 10ms audio length
        is_speech = vad.is_speech(pcm_data.tobytes(), samplerate)

        if is_speech:
            silence_count = 0  # Reset silence count when speech is detected
        else:
            silence_count += 1  # Increment silence count when no speech is detected

        if silence_count > silence_threshold:
            print("⏹️ Silence detected, stopping recording.")
            break

    # Cleanup
    stream.stop_stream()
    stream.close()
    p.terminate()

    # If stopped by request and no frames were captured, return None
    if _should_stop_audio and not frames:
        print("🛑 Recording stopped by request with no audio captured.")
        return None

    # Save to a temporary WAV file
    temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    with wave.open(temp_wav.name, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
        wf.setframerate(samplerate)
        wf.writeframes(b''.join(frames))

    print(f"✅ Audio recorded: {temp_wav.name}")
    return temp_wav.name


def transcribe_audio(file_path):
    """
    Transcribes the recorded audio file using Deepgram's API.
    
    Parameters:
      - file_path: The path to the audio file to transcribe.
    
    Returns:
      The transcribed text, or None if an error occurs.
    """
    try:
        with open(file_path, "rb") as file:
            buffer_data = file.read()

        payload: FileSource = {
            "buffer": buffer_data,
        }

        options = PrerecordedOptions(
            smart_format=True,
            summarize="v2",
        )

        # Call Deepgram API to transcribe the file
        file_response = deepgram.listen.rest.v("1").transcribe_file(payload, options)
        json_response = file_response  # Assuming the response is a JSON-like dict

        # Extract transcription text from the response
        transcript = json_response["results"]["channels"][0]["alternatives"][0]["transcript"]
        print(f"📝 Transcribed Text: {transcript}")
        return transcript

    except Exception as e:
        print(f"❌ Deepgram Exception: {e}")
        return None

def listen():
    """
    Records audio from the microphone and returns the transcribed text.
    
    Returns:
      The transcribed text as a string, or an empty string on failure.
    """
    audio_file = record_audio()
    if audio_file:
        transcript = transcribe_audio(audio_file)
        return transcript if transcript else ""
    return ""


