# File: /database/firestore.py
from google.cloud import firestore
from google.cloud.firestore_v1 import Client
from config.settings import settings
import json

class FirestoreClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            credentials = json.loads(settings.firestore_credentials)
            cls._instance.client = firestore.Client.from_service_account_info(credentials)
        return cls._instance

    def get_user(self, user_id: str):
        doc = self.client.collection("users").document(user_id).get()
        if not doc.exists:
            return None
        return doc.to_dict()

    def save_chat(self, user_id: str, message: str, response: str):
        self.client.collection("chat_history").add({
            "user_id": user_id,
            "message": message,
            "response": response,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
