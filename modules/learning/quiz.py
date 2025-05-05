import logging

logger = logging.getLogger(__name__)

class QuizManager:
    def create_quiz(self, user_id: str) -> str:
        # Giả lập tạo quiz
        quiz_id = "quiz_123"
        logger.info(f"Đã tạo quiz cho user {user_id}: {quiz_id}")
        return quiz_id

    def take_quiz(self, user_id: str) -> str:
        # Giả lập tham gia quiz
        result = "Bạn đã hoàn thành quiz! Điểm: 8/10"
        logger.info(f"User {user_id} đã tham gia quiz: {result}")
        return result
