
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
# /database/firestore.py
    def save_training_data(self, user_id: str, info: str, data_type: str = None) -> str:
        embedding = self._model.encode(info).tolist()
        doc_ref = self.client.collection("users").document(user_id).collection("training_data").document()
        # Phân loại thông tin
        if data_type is None:
            if info.lower().startswith("tôi tên"):
                data_type = "name"
            elif "sinh năm" in info.lower():
                data_type = "age"
            elif "nhà ở" in info.lower():
                data_type = "address"
            else:
                data_type = "general"
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
            data_embedding = np.array(data["embedding"])
            similarity = np.dot(query_embedding, data_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(data_embedding)
            )
            if similarity > 0.7:
                results.append({"id": doc.id, "info": data["info"], "type": data["type"], "similarity": similarity})
        return sorted(results, key=lambda x: x["similarity"], reverse=True) if results else []

    def get_similar_chat(self, user_id: str, query: str) -> Dict | None:
        query_embedding = self._model.encode(query).tolist()
        docs = self.client.collection("chat_history")\
            .where("user_id", "==", user_id)\
            .order_by("timestamp", direction=firestore.Query.DESCENDING)\
            .limit(10).stream()
        for doc in docs:
            data = doc.to_dict()
            message_embedding = self._model.encode(data["message"]).tolist()
            similarity = np.dot(query_embedding, message_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(message_embedding)
            )
            if similarity > 0.9:
                return {
                    "message": data["message"],
                    "response": data["response"],
                    "timestamp": data["timestamp"],
                    "similarity": similarity
                }
        return None

    def get_chat_history(self, user_id: str, limit: int = 5) -> List[Dict]:
        docs = self.client.collection("chat_history")\
            .where("user_id", "==", user_id)\
            .order_by("timestamp", direction=firestore.Query.DESCENDING)\
            .limit(limit).stream()
        return [doc.to_dict() for doc in docs]

    def get_training_data_count(self, user_id: str) -> int:
        docs = self.client.collection("users").document(user_id).collection("training_data").stream()
        return sum(1 for _ in docs)

    def get_latest_training_data_timestamp(self, user_id: str) -> float | None:
        docs = self.client.collection("users").document(user_id).collection("training_data")\
            .order_by("created_at", direction=firestore.Query.DESCENDING)\
            .limit(1).stream()
        for doc in docs:
            return doc.to_dict()["created_at"].timestamp()
        return None

    def set_admin(self, user_id: str, name: str = "Admin"):
        self.save_user(user_id, {
            "role": "admin",
            "name": name,
            "created_at": self.SERVER_TIMESTAMP
        })
        logger.info(f"User {user_id} set as admin with name {name}")
