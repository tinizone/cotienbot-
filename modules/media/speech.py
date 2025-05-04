import speech_recognition as sr

class SpeechProcessor:
    async def speech_to_text(self, audio_data: bytes) -> dict:
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_data) as source:
            audio = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio, language="vi-VN")
            return {"status": "success", "text": text}
        except sr.UnknownValueError:
            return {"status": "error", "message": "Could not understand audio"}
        except sr.RequestError as e:
            return {"status": "error", "message": f"Speech recognition error: {str(e)}"}
