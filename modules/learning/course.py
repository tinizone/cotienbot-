# File: /modules/learning/course.py
from database.firestore import FirestoreClient
from google.cloud import firestore

class CourseManager:
    def __init__(self):
        self.db = FirestoreClient()

    def create_course(self, title: str, description: str, admin_id: str):
        if not title or len(title) > 100:
            raise ValueError("Title must be non-empty and <= 100 characters")
        user = self.db.get_user(admin_id)
        if not user or user.get("role") != "admin":
            raise ValueError("Only admins can create courses")
        course_data = {
            "title": title,
            "description": description,
            "admin_id": admin_id,
            "created_at": firestore.SERVER_TIMESTAMP
        }
        self.db.client.collection("courses").add(course_data)
