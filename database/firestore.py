# File: /database/firestore.py
from google.cloud import firestore
from google.cloud.firestore_v1 import Client
from config.settings import settings
import json
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import numpy as np
import logging

logger = logging.getLogger(__name__)  # Thêm logging để debug

class FirestoreClient:
    _instance = None
    _model = SentenceTransformer("all-MiniLM-L6-v2")  # Nhẹ, miễn phí

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

    def save_user(self, user_id: str, data: Dict):
        """Lưu hoặc cập nhật thông tin người dùng."""
        self.client.collection("users").document(user_id).set(data, merge=True)

    def save_chat(self, user_id: str, message: str, response: str):
        self.client.collection("chat_history").add({
            "user_id": user_id,
            "message": message,
            "response": response,
            "timestamp": firestore.SERVER_TIMESTAMP
        })

    def save_training_data(self, user_id: str, info: str, data_type: str) -> str:
        """Lưu dữ liệu đào tạo với embedding."""
        embedding = self._model.encode(info).tolist()  # Tạo embedding
        doc_ref = self.client.collection("users").document(user_id).collection("training_data").document()
        doc_ref.set({
            "info": info,
            "type": data_type,
            "embedding": embedding,
            "created_at": firestore.SERVER_TIMESTAMP
        })
        return doc_ref.id

    def get_training_data(self, user_id: str, query: str) -> List[Dict]:
        """Tìm dữ liệu đào tạo liên quan đến query."""
        query_embedding = self._model.encode(query).tolist()
        docs = self.client.collection("users").document(user_id).collection("training_data").stream()
        results = []
        for doc in docs:
            data = doc.to_dict()
            data_embedding = np.array(data["embedding"])
            similarity = np.dot(query_embedding, data_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(data_embedding)
            )
            if similarity > 0.7:  # Ngưỡng tương đồng
                results.append({"id": doc.id, "info": data["info"], "type": data["type"], "similarity": similarity})
        return sorted(results, key=lambda x: x["similarity"], reverse=True)

    # NEW: Thêm hàm set_admin để hỗ trợ đặt admin
    def set_admin(self, user_id: str, name: str = "Admin"):
        """Thêm hoặc cập nhật user thành admin."""
        self.save_user(user_id, {
            "role": "admin",
            "name": name,
            "created_at": firestore.SERVER_TIMESTAMP
        })
        logger.info(f"User {user_id} set as admin with name {name}")
