# (/modules/learning/quiz.py)
from database.firestore import FirestoreClient
from google.cloud import firestore
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class QuizManager:
    def __init__(self):
        self.db = FirestoreClient()
        self.collection = self.db.client.collection("quizzes")

    def create_quiz(self, user_id: str, question: str, correct_answer: str, wrong_answers: List[str]) -> str:
        """Tạo quiz mới, chỉ admin được phép."""
        if not question or not correct_answer or len(wrong_answers) != 3:
            raise ValueError("Question, correct answer, and exactly 3 wrong answers are required")
        user = self.db.get_user(user_id)
        if not user or user.get("role") != "admin":
            raise ValueError("Only admins can create quizzes")
        quiz_data = {
            "user_id": user_id,
            "question": question,
            "correct_answer": correct_answer,
            "wrong_answers": wrong_answers,
            "created_at": firestore.SERVER_TIMESTAMP
        }
        doc_ref = self.collection.document()
        doc_ref.set(quiz_data)
        logger.info(f"Quiz created by {user_id}: {question}")
        return doc_ref.id

    def get_quiz(self, quiz_id: str) -> Dict:
        """Lấy thông tin quiz."""
        doc = self.collection.document(quiz_id).get()
        if not doc.exists:
            return {"status": "error", "message": "Quiz not found"}
        return {"status": "success", "quiz": doc.to_dict()}

    def list_quizzes(self, user_id: str) -> List[Dict]:
        """Liệt kê tất cả quiz."""
        docs = self.collection.stream()
        quizzes = [{"id": doc.id, **doc.to_dict()} for doc in docs]
        logger.info(f"Retrieved {len(quizzes)} quizzes for user {user_id}")
        return quizzes

    def check_answer(self, quiz_id: str, answer: str) -> Dict:
        """Kiểm tra đáp án người dùng."""
        quiz = self.get_quiz(quiz_id)
        if quiz["status"] != "success":
            return quiz
        correct = quiz["quiz"]["correct_answer"] == answer
        return {
            "status": "success",
            "correct": correct,
            "message": "Đúng!" if correct else f"Sai! Đáp án đúng là: {quiz['quiz']['correct_answer']}"
        }
