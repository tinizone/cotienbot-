# File: /database/firestore.py
import logging
from config.settings import settings
import json
from typing import List, Dict
import numpy as np

logger = logging.getLogger(__name__)

class FirestoreClient:
    def __init__(self):
        logger.info("Đang khởi tạo FirestoreClient (trong __init__)...")
        from google.cloud import firestore
        from google.cloud.firestore_v1 import Client
        from google.cloud.exceptions import GoogleCloudError
        self.GoogleCloudError = GoogleCloudError
        credentials = json.loads(settings.firestore_credentials)
        self.client = firestore.Client.from_service_account_info(credentials)
        self.SERVER_TIMESTAMP = firestore.SERVER_TIMESTAMP
        self._model = None
        self.chat_buffer = {}
        self.training_buffer = {}
        self.training_embeddings = {}
        self.BATCH_SIZE = 10
        self.MAX_CHATS = 50
        self.MAX_TRAINING = 50
        self.training_cache = {}
        self.similar_chat_cache = {}
        self.embedding_cache = {}
        self.chat_history_cache = {}
        self.training_data_cache = {}
        logger.info("Hoàn tất khởi tạo FirestoreClient (trong __init__)")

    def _load_model(self):
        if self._model is None:
            logger.info("Đang tải mô hình Sentence Transformers...")
            from sentence_transformers import SentenceTransformer
            from tenacity import retry, stop_after_attempt, wait_fixed
            @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
            def load_with_retry():
                return SentenceTransformer("sentence-transformers/all-MiniLM-L12-v2")
            self._model = load_with_retry()
        return self._model

    def _get_embedding(self, text: str) -> list:
        if text in self.embedding_cache:
            return self.embedding_cache[text]
        model = self._load_model()
        embedding = model.encode(text).tolist()
        self.embedding_cache[text] = embedding
        return embedding

    def save_chat(self, user_id: str, message: str, response: str, is_gemini: bool = False) -> None:
        try:
            if user_id not in self.chat_buffer:
                self.chat_buffer[user_id] = []
            self.chat_buffer[user_id].append({
                "message": message,
                "response": response,
                "is_gemini": is_gemini,
                "timestamp": self.SERVER_TIMESTAMP
            })

            # Cập nhật cache
            if user_id in self.chat_history_cache:
                self.chat_history_cache[user_id].append(self.chat_buffer[user_id][-1])

            if len(self.chat_buffer[user_id]) >= self.BATCH_SIZE:
                doc_ref = self.client.collection("chat_history").document(user_id)
                current_chats = doc_ref.get().to_dict().get("chats", []) if doc_ref.get().exists else []
                current_chats.extend(self.chat_buffer[user_id])
                current_chats = current_chats[-self.MAX_CHATS:]
                doc_ref.set({"chats": current_chats})
                self.chat_buffer[user_id] = []
                # Cập nhật cache sau khi lưu
                self.chat_history_cache[user_id] = current_chats
                logger.info(f"Đã lưu lô trò chuyện cho người dùng {user_id}")
        except self.GoogleCloudError as e:
            logger.error(f"Lỗi khi lưu trò chuyện cho người dùng {user_id}: {str(e)}")
            raise

    def get_similar_chat(self, user_id: str, message: str) -> Dict | None:
        try:
            import numpy as np
            cache_key = f"{user_id}:{message}"
            if cache_key in self.similar_chat_cache:
                logger.info(f"Trả lời từ cache lịch sử trò chuyện cho user {user_id}")
                return self.similar_chat_cache[cache_key]

            # Kiểm tra cache lịch sử trò chuyện
            if user_id not in self.chat_history_cache:
                doc = self.client.collection("chat_history").document(user_id).get()
                chats = doc.to_dict().get("chats", []) if doc.exists else []
                self.chat_history_cache[user_id] = chats
            chats = self.chat_history_cache[user_id]
            if not chats:
                return None

            # Sử dụng embedding để tìm tin nhắn tương tự
            message_embedding = self._get_embedding(message)
            best_match = None
            highest_similarity = 0.0
            for chat in chats:
                chat_message = chat["message"]
                chat_embedding = self._get_embedding(chat_message)
                similarity = np.dot(message_embedding, chat_embedding) / (
                    np.linalg.norm(message_embedding) * np.linalg.norm(chat_embedding)
                )
                if similarity > 0.7 and similarity > highest_similarity:
                    highest_similarity = similarity
                    best_match = chat
            if best_match:
                self.similar_chat_cache[cache_key] = best_match
                return best_match
            return None
        except self.GoogleCloudError as e:
            logger.error(f"Lỗi khi tìm trò chuyện tương tự cho người dùng {user_id}: {str(e)}")
            raise

    def save_training_data(self, user_id: str, info: str) -> str:
        try:
            embedding = self._get_embedding(info)
            if user_id not in self.training_buffer:
                self.training_buffer[user_id] = []
            if user_id not in self.training_embeddings:
                self.training_embeddings[user_id] = {}
            self.training_buffer[user_id].append({
                "info": info,
                "created_at": self.SERVER_TIMESTAMP
            })
            self.training_embeddings[user_id][info] = embedding

            # Cập nhật cache
            if user_id in self.training_data_cache:
                self.training_data_cache[user_id].append(self.training_buffer[user_id][-1])

            if len(self.training_buffer[user_id]) >= self.BATCH_SIZE:
                doc_ref = self.client.collection("users").document(user_id)
                current_training = doc_ref.get().to_dict().get("training_data", []) if doc_ref.get().exists else []
                current_training.extend(self.training_buffer[user_id])
                current_training = current_training[-self.MAX_TRAINING:]
                doc_ref.set({"training_data": current_training})
                self.training_buffer[user_id] = []
                # Cập nhật cache sau khi lưu
                self.training_data_cache[user_id] = current_training
                logger.info(f"Đã lưu lô dữ liệu huấn luyện cho người dùng {user_id}")
            return "buffered"
        except self.GoogleCloudError as e:
            logger.error(f"Lỗi khi lưu dữ liệu huấn luyện cho người dùng {user_id}: {str(e)}")
            raise

    def get_training_data(self, user_id: str, query: str) -> List[Dict]:
        try:
            import numpy as np
            cache_key = f"{user_id}:{query}"
            if cache_key in self.training_cache:
                logger.info(f"Trả lời từ cache dữ liệu huấn luyện cho user {user_id}")
                return self.training_cache[cache_key]

            # Kiểm tra cache dữ liệu huấn luyện
            if user_id not in self.training_data_cache:
                doc = self.client.collection("users").document(user_id).get()
                training_data = doc.to_dict().get("training_data", []) if doc.exists else []
                self.training_data_cache[user_id] = training_data
            training_data = self.training_data_cache[user_id]

            query_embedding = self._get_embedding(query)
            results = []
            for i, data in enumerate(training_data):
                info = data["info"]
                if info.lower() == query.lower():
                    results.append({"id": f"item_{i}", "info": info, "similarity": 1.0})
                    continue
                data_embedding = self.training_embeddings.get(user_id, {}).get(info)
                if not data_embedding:
                    continue
                similarity = np.dot(query_embedding, data_embedding) / (
                    np.linalg.norm(query_embedding) * np.linalg.norm(data_embedding)
                )
                if similarity > 0.6:
                    results.append({"id": f"item_{i}", "info": info, "similarity": similarity})
            results = sorted(results, key=lambda x: x["similarity"], reverse=True)
            self.training_cache[cache_key] = results
            return results
        except self.GoogleCloudError as e:
            logger.error(f"Lỗi khi lấy dữ liệu huấn luyện cho người dùng {user_id}: {str(e)}")
            raise
