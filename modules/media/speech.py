# File: /modules/media/speech.py
import logging
import speech_recognition as sr
from io import BytesIO
from typing import Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SpeechProcessor:
    async def speech_to_text(self, audio_data: bytes) -> Dict:
        """Chuyển giọng nói thành văn bản."""
        try:
            recognizer = sr.Recognizer()
            with sr.AudioFile(BytesIO(audio_data)) as source:
                audio = recognizer.record(source)
            text = recognizer.recognize_google(audio, language="vi-VN")
            logger.info("Speech converted to text successfully")
            return {"status": "success", "text": text}
        except Exception as e:
            logger.error(f"Error converting speech: {str(e)}")
            return {"status": "error", "message": str(e)}
