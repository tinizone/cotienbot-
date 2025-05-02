from google.cloud import firestore
from google.cloud.firestore_v1 import Client
from config.settings import settings
import json

class FirestoreClient:
    def __init__(self):
        credentials = json.loads(settings.firestore_credentials)
        self.client = firestore.Client.from_service_account_info(credentials)

    def get_user(self, user_id: str):
        return self.client.collection("users").document(user_id).get()

    def save_chat(self, user_id: str, message: str, response: str):
        self.client.collection("chat_history").add({
            "user_id": user_id,
            "message": message,
            "response": response,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
