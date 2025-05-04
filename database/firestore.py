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
        self._model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")  # Multilingual model

    def get_user(self, user_id: str) -> Dict | None:
        """Retrieve user data by ID."""
        try:
            doc = self.client.collection("users").document(user_id).get()
            return doc.to_dict() if doc.exists else None
        except GoogleCloudError as e:
            logger.error(f"Error fetching user {user_id}: {str(e)}")
            raise

    def save_user(self, user_id: str, data: Dict) -> None:
        """Save or update user data."""
        try:
            self.client.collection("users").document(user_id).set(data, merge=True)
            logger.info(f"Saved user data for {user_id}")
        except GoogleCloudError as e:
            logger.error(f"Error saving user {user_id}: {str(e)}")
            raise

    def save_chat(self, user_id: str, message: str, response: str) -> None:
        """Save chat history."""
        try:
            self.client.collection("chat_history").add({
                "user_id": user_id,
                "message": message,
                "response": response,
                "timestamp": self.SERVER_TIMESTAMP
            })
            logger.info(f"Saved chat for user {user_id}")
        except GoogleCloudError as e:
            logger.error(f"Error saving chat for user {user_id}: {str(e)}")
            raise

    def get_chat_history(self, user_id: str, limit: int = 5) -> List[Dict]:
        """Retrieve recent chat history for a user."""
        try:
            docs = self.client.collection("chat_history")\
                .where("user_id", "==", user_id)\
                .order_by("timestamp", direction=firestore.Query.DESCENDING)\
                .limit(limit).stream()
            return [doc.to_dict() for doc in docs]
        except GoogleCloudError as e:
            logger.error(f"Error fetching chat history for user {user_id}: {str(e)}")
            raise

    def get_similar_chat(self, user_id: str, message: str) -> Dict | None:
        """Find a similar chat message using exact match for simplicity."""
        try:
            docs = self.client.collection("chat_history")\
                .where("user_id", "==", user_id)\
                .where("message", "==", message.lower())\
                .limit(1).stream()
            for doc in docs:
                return doc.to_dict()
            return None
        except GoogleCloudError as e:
            logger.error(f"Error fetching similar chat for user {user_id}: {str(e)}")
            raise

    def save_training_data(self, user_id: str, info: str, data_type: str) -> str:
        """Save training data with embeddings."""
        try:
            embedding = self._model.encode(info).tolist()
            doc_ref = self.client.collection("users").document(user_id).collection("training_data").document()
            doc_ref.set({
                "info": info,
                "type": data_type,
                "embedding": embedding,
                "created_at": self.SERVER_TIMESTAMP
            })
            logger.info(f"Saved training data for user {user_id}, doc ID: {doc_ref.id}")
            return doc_ref.id
        except GoogleCloudError as e:
            logger.error(f"Error saving training data for user {user_id}: {str(e)}")
            raise

    def get_training_data(self, user_id: str, query: str) -> List[Dict]:
        """Retrieve training data based on text or embedding similarity."""
        try:
            query_embedding = self._model.encode(query).tolist()
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
                if similarity > 0.5:  # Increased threshold for better precision
                    results.append({"id": doc.id, "info": data["info"], "type": data["type"], "similarity": similarity})
            return sorted(results, key=lambda x: x["similarity"], reverse=True)
        except GoogleCloudError as e:
            logger.error(f"Error fetching training data for user {user_id}: {str(e)}")
            raise

    def get_latest_training_data_timestamp(self, user_id: str) -> float | None:
        """Get the timestamp of the latest training data."""
        try:
            docs = self.client.collection("users").document(user_id).collection("training_data")\
                .order_by("created_at", direction=firestore.Query.DESCENDING).limit(1).stream()
            for doc in docs:
                return doc.to_dict()["created_at"].timestamp()
            return None
        except GoogleCloudError as e:
            logger.error(f"Error fetching latest training timestamp for user {user_id}: {str(e)}")
            raise

    def set_admin(self, user_id: str, name: str = "Admin") -> None:
        """Set a user as admin."""
        try:
            self.save_user(user_id, {
                "role": "admin",
                "name": name,
                "created_at": self.SERVER_TIMESTAMP
            })
            logger.info(f"User {user_id} set as admin with name {name}")
        except GoogleCloudError as e:
            logger.error(f"Error setting admin for user {user_id}: {str(e)}")
            raise
