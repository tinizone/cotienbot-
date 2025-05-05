
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
        self.chat_buffer = {}
        self.training_buffer = {}
        self.knowledge_graph = {}  # Đồ thị tri thức: {user_id: {entity: {attribute: value}}}
        self.BATCH_SIZE = 10
        self.MAX_CHATS = 50
        self.MAX_TRAINING = 50
        self.training_cache = {}
        self.similar_chat_cache = {}
        self.chat_history_cache = {}
        self.training_data_cache = {}
        logger.info("Hoàn tất khởi tạo FirestoreClient (trong __init__)")

    def _extract_entities(self, text: str) -> Dict:
        # Phân tích cú pháp đơn giản để trích xuất thực thể và thuộc tính
        text = text.lower()
        if "tôi tên là" in text:
            name = text.split("tôi tên là")[-1].strip()
            return {"entity": "user", "attribute": "name", "value": name}
        elif "nhà tôi có" in text:
            parts = text.split("nhà tôi có")[-1].strip().split()
            if len(parts) >= 2 and parts[0].isdigit():
                count = parts[0]
                entity = " ".join(parts[1:])
                return {"entity": "house", "attribute": "has", "value": f"{count} {entity}"}
        return None

    def _query_knowledge_graph(self, user_id: str, query: str) -> str | None:
        # Truy vấn đồ thị tri thức dựa trên từ khóa và mối quan hệ
        query = query.lower()
        if user_id not in self.knowledge_graph:
            return None

        if "tôi tên gì" in query:
            user_data = self.knowledge_graph[user_id].get("user", {})
            return user_data.get("name")
        elif "nhà tôi có bao nhiêu" in query:
            house_data = self.knowledge_graph[user_id].get("house", {})
            return house_data.get("has")
        return None

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

            # So khớp chính xác (có thể cải thiện bằng embedding nếu cần)
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
            # Phân tích và lưu vào đồ thị tri thức
            entities = self._extract_entities(info)
            if entities:
                if user_id not in self.knowledge_graph:
                    self.knowledge_graph[user_id] = {}
                entity = entities["entity"]
                if entity not in self.knowledge_graph[user_id]:
                    self.knowledge_graph[user_id][entity] = {}
                self.knowledge_graph[user_id][entity][entities["attribute"]] = entities["value"]
                logger.info(f"Đã lưu vào đồ thị tri thức: {user_id} - {entity} - {entities['attribute']} - {entities['value']}")

            # Lưu vào Firestore như trước
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
                logger.info(f"Đã lưu lô dữ liệu huấn luyện cho người dùng {user_id}")
            return "buffered"
        except self.GoogleCloudError as e:
            logger.error(f"Lỗi khi lưu dữ liệu huấn luyện cho người dùng {user_id}: {str(e)}")
            raise

    def get_training_data(self, user_id: str, query: str) -> List[Dict]:
        try:
            cache_key = f"{user_id}:{query}"
            if cache_key in self.training_cache:
                logger.info(f"Trả lời từ cache dữ liệu huấn luyện cho user {user_id}")
                return self.training_cache[cache_key]

            # Truy vấn từ đồ thị tri thức trước
            kg_result = self._query_knowledge_graph(user_id, query)
            if kg_result:
                result = [{"id": "kg_1", "info": kg_result, "similarity": 1.0}]
                self.training_cache[cache_key] = result
                return result

            # Nếu không tìm thấy trong đồ thị, lấy từ Firestore (danh sách dữ liệu gốc)
            if user_id not in self.training_data_cache:
                doc = self.client.collection("users").document(user_id).get()
                training_data = doc.to_dict().get("training_data", []) if doc.exists else []
                self.training_data_cache[user_id] = training_data
            training_data = self.training_data_cache[user_id]

            # Tìm kiếm đơn giản nếu đồ thị không có
            results = []
            for i, data in enumerate(training_data):
                info = data["info"]
                if query.lower() in info.lower():
                    results.append({"id": f"item_{i}", "info": info, "similarity": 1.0})
            self.training_cache[cache_key] = results
            return results
        except self.GoogleCloudError as e:
            logger.error(f"Lỗi khi lấy dữ liệu huấn luyện cho người dùng {user_id}: {str(e)}")
            raise
