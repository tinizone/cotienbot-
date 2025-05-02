from database.firestore import FirestoreClient

class CourseManager:
    def __init__(self):
        self.db = FirestoreClient()

    def create_course(self, title: str, description: str, admin_id: str):
        course_data = {
            "title": title,
            "description": description,
            "admin_id": admin_id,
            "created_at": firestore.SERVER_TIMESTAMP
        }
        self.db.client.collection("courses").add(course_data)
