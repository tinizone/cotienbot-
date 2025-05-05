# UPDATE: /modules/learning/quiz.py
from database.firestore import FirestoreClient
from google.cloud import firestore
from google.cloud.exceptions import GoogleCloudError
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)

class QuizManager:
    def __init__(self, db: FirestoreClient = None):
        self.db = db or FirestoreClient()
        self.collection = self.db.client.collection("quizzes")

    def create_quiz(self, user_id: str, question: str, correct_answer: str, wrong_answers: List[str]) -> str:
        """Create a new quiz (admin only)."""
        try:
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
        except GoogleCloudError as e:
            logger.error(f"Error creating quiz by {user_id}: {str(e)}")
            raise
        except ValueError as e:
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating quiz by {user_id}: {str(e)}")
            raise

    def get_quiz(self, quiz_id: str) -> Dict:
        """Retrieve quiz information."""
        try:
            doc = self.collection.document(quiz_id).get()
            if not doc.exists:
                return {"status": "error", "message": "Quiz not found"}
            return {"status": "success", "quiz": doc.to_dict()}
        except GoogleCloudError as e:
            logger.error(f"Error fetching quiz {quiz_id}: {str(e)}")
            return {"status": "error", "message": str(e)}

    def list_quizzes(self, user_id: str) -> List[Dict]:
        """List all quizzes."""
        try:
            docs = self.collection.stream()
            quizzes = [{"id": doc.id, **doc.to_dict()} for doc in docs]
            logger.info(f"Retrieved {len(quizzes)} quizzes for user {user_id}")
            return quizzes
        except GoogleCloudError as e:
            logger.error(f"Error listing quizzes for user {user_id}: {str(e)}")
            return []

    def check_answer(self, quiz_id: str, answer: str) -> Dict:
        """Check user's answer for a quiz."""
        quiz = self.get_quiz(quiz_id)
        if quiz["status"] != "success":
            return quiz
        correct = quiz["quiz"]["correct_answer"] == answer
        return {
            "status": "success",
            "correct": correct,
            "message": "Đúng!" if correct else f"Sai! Đáp án đúng là: {quiz['quiz']['correct_answer']}"
        }
