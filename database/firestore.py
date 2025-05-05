import logging
from config.settings import settings
import json
from typing import List, Dict
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import os

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
        self.chat_buffer = {}
        self.training_buffer = {}
        self.training_data_cache = {}
        self.BATCH_SIZE = 10
        self.MAX_CHATS = 50
        self.MAX_TRAINING = 1000000  # Không giới hạn cho ID của bạn
        self.training_cache = {}
        self.similar_chat_cache = {}
        self.chat_history_cache = {}
        self.model = SentenceTransformer("all-MiniLM-L12-v2")
        self.index = None
        self.data_map = {}
        self.index_path = "./index.faiss"  # Lưu trong thư mục Spaces
        self._load_training_data_and_build_index()
        logger.info("Hoàn tất khởi tạo FirestoreClient (trong __init__)")

    def _load_training_data_and_build_index(self):
        try:
            user_id = "your_user_id_here"  # Thay bằng ID Telegram của bạn
            doc = self.client.collection("users").document(user_id).get(timeout=10)
            if doc.exists:
                training_data = doc.to_dict().get("training_data", [])
                self.training_data_cache[user_id] = training_data
                embeddings = self.model.encode([item["info"] for item in training_data], convert_to_numpy=True)
                self.index = faiss.IndexFlatL2(embeddings.shape[1])
                self.index.add(embeddings)
                faiss.write_index(self.index, self.index_path)
                self.data_map = {i: item["info"] for i, item in enumerate(training_data)}
            else:
                logger.info(f"Không tìm thấy dữ liệu huấn luyện cho user {user_id}")
        except self.GoogleCloudError as e:
            logger.error(f"Lỗi khi tải dữ liệu huấn luyện: {str(e)}")

    def _load_index(self):
        if self.index is None:
            if os.path.exists(self.index_path):
                self.index = faiss.read_index(self.index_path)
            else:
                self.index = faiss.IndexFlatL2(384)  # 384 chiều của all-MiniLM-L12-v2
        return self.index

    def _filter_relevant_data(self, query: str, user_id: str, top_k=10) -> List[str]:
        query_embedding = self.model.encode([query], convert_to_numpy=True)
        index = self._load_index()
        distances, indices = index.search(query_embedding, top_k)
        relevant_data = []
        for idx, dist in zip(indices[0], distances[0]):
            if dist < 1.0:  # Ngưỡng tương đồng
                relevant_data.append(self.data_map.get(idx, ""))
        return relevant_data[:top_k]

    def _update_vector_index(self, user_id, training_data):
        embeddings = self.model.encode([item["info"] for item in training_data], convert_to_numpy=True)
        index = self._load_index()
        index.add(embeddings)
        faiss.write_index(index, self.index_path)
        self.data_map.update({len(self.data_map) + i: item["info"] for i, item in enumerate(training_data)})

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
            if user_id in self.chat_history_cache:
                self.chat_history_cache[user_id].append(self.chat_buffer[user_id][-1])
            if len(self.chat_buffer[user_id]) >= self.BATCH_SIZE:
                doc_ref = self.client.collection("chat_history").document(user_id)
                current_chats = doc_ref.get().to_dict().get("chats", []) if doc_ref.get().exists else []
                current_chats.extend(self.chat_buffer[user_id])
                current_chats = current_chats[-self.MAX_CHATS:]
                doc_ref.set({"chats": current_chats})
                self.chat_history_cache[user_id] = current_chats
                self.chat_buffer[user_id] = []
                logger.info(f"Đã lưu lô trò chuyện cho người dùng {user_id}")
        except self.GoogleCloudError as e:
            logger.error(f"Lỗi khi lưu trò chuyện cho người dùng {user_id}: {str(e)}")
            raise

    def get_similar_chat(self, user_id: str, message: str) -> Dict | None:
        try:
            cache_key = f"{user_id}:{message}"
            if cache_key in self.similar_chat_cache:
                logger.info(f"Trả lời từ cache lịch sử trò chuyện cho user {user_id}")
                return self.similar_chat_cache[cache_key]
            if user_id not in self.chat_history_cache:
                doc = self.client.collection("chat_history").document(user_id).get()
                chats = doc.to_dict().get("chats", []) if doc.exists else []
                self.chat_history_cache[user_id] = chats
            chats = self.chat_history_cache[user_id]
            if not chats:
                return None
            for chat in chats:
                if chat["message"].lower() == message.lower():
                    self.similar_chat_cache[cache_key] = chat
                    return chat
            return None
        except self.GoogleCloudError as e:
            logger.error(f"Lỗi khi tìm trò chuyện tương tự cho người dùng {user_id}: {str(e)}")
            raise

    def save_training_data(self, user_id: str, info: str) -> str:
        try:
            if user_id == "your_user_id_here":  # Chỉ cho phép ID của bạn không giới hạn
                if user_id not in self.training_buffer:
                    self.training_buffer[user_id] = []
                self.training_buffer[user_id].append({
                    "info": info,
                    "created_at": self.SERVER_TIMESTAMP
                })
                if user_id not in self.training_data_cache:
                    self.training_data_cache[user_id] = []
                self.training_data_cache[user_id].append(self.training_buffer[user_id][-1])

                if len(self.training_buffer[user_id]) >= self.BATCH_SIZE:
                    doc_ref = self.client.collection("users").document(user_id)
                    current_training = doc_ref.get().to_dict().get("training_data", []) if doc_ref.get().exists else []
                    current_training.extend(self.training_buffer[user_id])
                    current_training = current_training[-self.MAX_TRAINING:]
                    doc_ref.set({"training_data": current_training})
                    self.training_data_cache[user_id] = current_training
                    self.training_buffer[user_id] = []
                    self._update_vector_index(user_id, current_training)
                    logger.info(f"Đã lưu lô dữ liệu huấn luyện cho người dùng {user_id}")
                return "buffered"
            else:
                logger.info(f"User {user_id} không được phép huấn luyện vượt giới hạn")
                return "restricted"
        except self.GoogleCloudError as e:
            logger.error(f"Lỗi khi lưu dữ liệu huấn luyện cho người dùng {user_id}: {str(e)}")
            raise

    def get_training_data(self, user_id: str, query: str) -> List[Dict]:
        try:
            cache_key = f"{user_id}:{query}"
            if cache_key in self.training_cache:
                logger.info(f"Trả lời từ cache dữ liệu huấn luyện cho user {user_id}")
                return self.training_cache[cache_key]

            if user_id != "your_user_id_here":
                return []

            relevant_data = self._filter_relevant_data(query, user_id)
            results = [{"id": f"item_{i}", "info": data, "similarity": 1.0} for i, data in enumerate(relevant_data)]
            self.training_cache[cache_key] = results
            return results
        except self.GoogleCloudError as e:
            logger.error(f"Lỗi khi lấy dữ liệu huấn luyện cho người dùng {user_id}: {str(e)}")
            raise
