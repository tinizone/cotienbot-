# File: /database/firestore.py
from google.cloud import firestore
from google.cloud.firestore_v1 import Client
from config.settings import settings
import json
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import numpy as np
import logging

logger = logging.getLogger(__name__)

class FirestoreClient:
    _instance = None
    _model = SentenceTransformer("all-MiniLM-L6-v2")

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            credentials = json.loads(settings.firestore_credentials)
            cls._instance.client = firestore.Client.from_service_account_info(credentials)
            cls._instance.SERVER_TIMESTAMP = firestore.SERVER_TIMESTAMP
        return cls._instance

    def get_user(self, user_id: str):
        doc = self.client.collection("users").document(user_id).get()
        if not doc.exists:
            return None
        return doc.to_dict()

    def save_user(self, user_id: str, data: Dict):
        self.client.collection("users").document(user_id).set(data, merge=True)

    def save_chat(self, user_id: str, message: str, response: str):
        self.client.collection("chat_history").add({
            "user_id": user_id,
            "message": message,
            "response": response,
            "timestamp": self.SERVER_TIMESTAMP
        })

    def save_training_data(self, user_id: str, info: str, data_type: str) -> str:
        embedding = self._model.encode(info).tolist()
        doc_ref = self.client.collection("users").document(user_id).collection("training_data").document()
        doc_ref.set({
            "info": info,
            "type": data_type,
            "embedding": embedding,
            "created_at": self.SERVER_TIMESTAMP
        })
        return doc_ref.id

    def get_training_data(self, user_id: str, query: str) -> List[Dict]:
        query_embedding = self._model.encode(query).tolist()
        docs = self.client.collection("users").document(user_id).collection("training_data").stream()
        results = []
        for doc in docs:
            data = doc.to_dict()
            # UPDATE: So sánh văn bản trực tiếp trước
            if data["info"].lower() == query.lower():
                results.append({"id": doc.id, "info": data["info"], "type": data["type"], "similarity": 1.0})
                continue
            # So sánh embedding
            data_embedding = np.array(data["embedding"])
            similarity = np.dot(query_embedding, data_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(data_embedding)
            )
            # UPDATE: Giảm ngưỡng similarity từ 0.5 xuống 0.3
            if similarity > 0.3:
                results.append({"id": doc.id, "info": data["info"], "type": data["type"], "similarity": similarity})
        return sorted(results, key=lambda x: x["similarity"], reverse=True)

    def set_admin(self, user_id: str, name: str = "Admin"):
        self.save_user(user_id, {
            "role": "admin",
            "name": name,
            "created_at": self.SERVER_TIMESTAMP
        })
        logger.info(f"User {user_id} set as admin with name {name}")
