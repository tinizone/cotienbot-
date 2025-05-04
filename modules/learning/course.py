# UPDATE: /modules/learning/course.py
from database.firestore import FirestoreClient
from google.cloud import firestore
from google.cloud.exceptions import GoogleCloudError
import logging

logger = logging.getLogger(__name__)

class CourseManager:
    def __init__(self, db: FirestoreClient = None):
        self.db = db or FirestoreClient()

    def create_course(self, title: str, description: str, admin_id: str) -> None:
        """Create a new course (admin only)."""
        try:
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
            logger.info(f"Course created by {admin_id}: {title}")
        except GoogleCloudError as e:
            logger.error(f"Error creating course by {admin_id}: {str(e)}")
            raise
        except ValueError as e:
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating course by {admin_id}: {str(e)}")
            raise
