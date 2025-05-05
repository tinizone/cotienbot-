import speech_recognition as sr
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

class SpeechProcessor:
    """Xử lý giọng nói thành văn bản với tối ưu bộ nhớ."""
    _recognizer = None

    @classmethod
    def _get_recognizer(cls):
        """Tải Recognizer chỉ khi cần, tránh tải trước."""
        if cls._recognizer is None:
            logger.info("Đang khởi tạo Recognizer cho SpeechProcessor...")
            cls._recognizer = sr.Recognizer()
        return cls._recognizer

    async def speech_to_text(self, audio_data: bytes) -> dict:
        """Chuyển đổi dữ liệu âm thanh thành văn bản."""
        try:
            recognizer = self._get_recognizer()
            with BytesIO(audio_data) as source:
                audio = recognizer.record(sr.AudioFile(source))
            text = recognizer.recognize_google(audio, language="vi-VN")
            logger.info("Chuyển đổi giọng nói thành công")
            return {"status": "success", "text": text}
        except sr.UnknownValueError:
            logger.error("Không nhận diện được giọng nói")
            return {"status": "error", "message": "Không nhận diện được giọng nói"}
        except sr.RequestError as e:
            logger.error(f"Lỗi khi gọi API nhận diện giọng nói: {str(e)}")
            return {"status": "error", "message": f"Lỗi API nhận diện: {str(e)}"}
        except Exception as e:
            logger.error(f"Lỗi bất ngờ khi xử lý giọng nói: {str(e)}")
            return {"status": "error", "message": f"Lỗi: {str(e)}"}
