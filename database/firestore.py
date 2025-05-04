# UPDATE: /database/firestore.py
from google.cloud import firestore
from google.cloud.firestore_v1 import Client
from config.settings import settings
import json
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import numpy as np
import logging
from google.cloud.exceptions import GoogleCloudError

logger = logging.getLogger(__name__)

class FirestoreClient:
    def __init__(self):
        credentials = json.loads(settings.firestore_credentials)
        self.client = firestore.Client.from_service_account_info(credentials)
        self.SERVER_TIMESTAMP = firestore.SERVER_TIMESTAMP
        self._model = None  # Khởi tạo mô hình khi cần

    def _load_model(self):
        """Tải mô hình Sentence Transformers khi cần."""
        if self._model is None:
            logger.info("Đang tải mô hình Sentence Transformers...")
            self._model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        return self._model

    def get_user(self, user_id: str) -> Dict | None:
        try:
            doc = self.client.collection("users").document(user_id).get()
            return doc.to_dict() if doc.exists else None
        except GoogleCloudError as e:
            logger.error(f"Lỗi khi lấy người dùng {user_id}: {str(e)}")
            raise

    def save_user(self, user_id: str, data: Dict) -> None:
        try:
            self.client.collection("users").document(user_id).set(data, merge=True)
            logger.info(f"Đã lưu dữ liệu người dùng {user_id}")
        except GoogleCloudError as e:
            logger.error(f"Lỗi khi lưu người dùng {user_id}: {str(e)}")
            raise

    def save_chat(self, user_id: str, message: str, response: str) -> None:
        try:
            self.client.collection("chat_history").add({
                "user_id": user_id,
                "message": message,
                "response": response,
                "timestamp": self.SERVER_TIMESTAMP
            })
            logger.info(f"Đã lưu trò chuyện cho người dùng {user_id}")
        except GoogleCloudError as e:
            logger.error(f"Lỗi khi lưu trò chuyện cho người dùng {user_id}: {str(e)}")
            raise

    def get_chat_history(self, user_id: str, limit: int = 5) -> List[Dict]:
        try:
            docs = self.client.collection("chat_history")\
                .where("user_id", "==", user_id)\
                .order_by("timestamp", direction=firestore.Query.DESCENDING)\
                .limit(limit).stream()
            return [doc.to_dict() for doc in docs]
        except GoogleCloudError as e:
            logger.error(f"Lỗi khi lấy lịch sử trò chuyện cho người dùng {user_id}: {str(e)}")
            raise

    def get_similar_chat(self, user_id: str, message: str) -> Dict | None:
        try:
            docs = self.client.collection("chat_history")\
                .where("user_id", "==", user_id)\
                .where("message", "==", message.lower())\
                .limit(1).stream()
            for doc in docs:
                return doc.to_dict()
            return None
        except GoogleCloudError as e:
            logger.error(f"Lỗi khi tìm trò chuyện tương tự cho người dùng {user_id}: {str(e)}")
            raise

    def save_training_data(self, user_id: str, info: str, data_type: str) -> str:
        try:
            model = self._load_model()
            embedding = model.encode(info).tolist()
            doc_ref = self.client.collection("users").document(user_id).collection("training_data").document()
            doc_ref.set({
                "info": info,
                "type": data_type,
                "embedding": embedding,
                "created_at": self.SERVER_TIMESTAMP
            })
            logger.info(f"Đã lưu dữ liệu huấn luyện cho người dùng {user_id}, ID: {doc_ref.id}")
            return doc_ref.id
        except GoogleCloudError as e:
            logger.error(f"Lỗi khi lưu dữ liệu huấn luyện cho người dùng {user_id}: {str(e)}")
            raise

    def get_training_data(self, user_id: str, query: str) -> List[Dict]:
        try:
            model = self._load_model()
            query_embedding = model.encode(query).tolist()
            docs = self.client.collection("users").document(user_id).collection("training_data").stream()
            results = []
            for doc in docs:
                data = doc.to_dict()
                if data["info"].lower() == query.lower():
                    results.append({"id": doc.id, "info": data["info"], "type": data["type"], "similarity": 1.0})
                    continue
                data_embedding = np.array(data["embedding"])
                similarity = np.dot(query_embedding, data_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(data_embedding)
                )
                if similarity > 0.7:
                    results.append({"id": doc.id, "info": data["info"], "type": data["type"], "similarity": similarity})
            return sorted(results, key=lambda x: x["similarity"], reverse=True)
        except GoogleCloudError as e:
            logger.error(f"Lỗi khi lấy dữ liệu huấn luyện cho người dùng {user_id}: {str(e)}")
            raise

    def get_latest_training_data_timestamp(self, user_id: str) -> float | None:
        try:
            docs = self.client.collection("users").document(user_id).collection("training_data")\
                .order_by("created_at", direction=firestore.Query.DESCENDING).limit(1).stream()
            for doc in docs:
                return doc.to_dict()["created_at"].timestamp()
            return None
        except GoogleCloudError as e:
            logger.error(f"Lỗi khi lấy thời gian huấn luyện mới nhất cho người dùng {user_id}: {str(e)}")
            raise

    def set_admin(self, user_id: str, name: str = "Admin") -> None:
        try:
            self.save_user(user_id, {
                "role": "admin",
                "name": name,
                "created_at": self.SERVER_TIMESTAMP
            })
            logger.info(f"Người dùng {user_id} được đặt làm admin với tên {name}")
        except GoogleCloudError as e:
            logger.error(f"Lỗi khi đặt admin cho người dùng {user_id}: {str(e)}")
            raise
