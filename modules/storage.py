# Đường dẫn: cotienbot/modules/storage.py
# Tên file: storage.py

import os
import json
import logging
from google.oauth2.service_account import Credentials
from google.cloud import firestore

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def _initialize_firestore():
    """Khởi tạo Firestore credentials."""
    try:
        # Kiểm tra biến môi trường trước
        logger.info("Checking Firestore credentials configuration")
        if not os.getenv("FIREBASE_CREDENTIALS") and not os.getenv("FIRESTORE_PROJECT_ID") and not os.path.exists(os.path.join(os.path.dirname(__file__), "../credentials.json")):
            raise ValueError("No Firestore credentials provided (FIREBASE_CREDENTIALS, FIRESTORE_PROJECT_ID, or credentials.json missing)")

        # Cách 1: Dùng file credentials.json (cho local hoặc Render.com nếu có file)
        credentials_path = os.path.join(os.path.dirname(__file__), "../credentials.json")
        if os.path.exists(credentials_path):
            credentials = Credentials.from_service_account_file(credentials_path)
            logger.info("Initialized Firestore with credentials.json")
            return credentials

        # Cách 2: Dùng biến môi trường FIREBASE_CREDENTIALS (cho Render.com)
        credentials_json = os.getenv("FIREBASE_CREDENTIALS")
        if credentials_json:
            credentials_dict = json.loads(credentials_json)
            credentials = Credentials.from_service_account_info(credentials_dict)
            logger.info("Initialized Firestore with FIREBASE_CREDENTIALS")
            return credentials

        # Fallback: Dùng project_id nếu không có credentials (cho môi trường tự xác thực)
        project_id = os.getenv("FIRESTORE_PROJECT_ID")
        if project_id:
            logger.info(f"Initialized Firestore with project_id: {project_id}")
            return firestore.Client(project=project_id)

        raise ValueError("Không tìm thấy credentials hoặc project_id để khởi tạo Firestore.")

    except Exception as e:
        logger.error(f"Firestore initialization error: {str(e)}")
        raise

def _get_firestore_client():
    """Lấy Firestore client, khởi tạo nếu chưa có."""
    credentials = _initialize_firestore()
    if isinstance(credentials, firestore.Client):
        return credentials
    return firestore.Client(credentials=credentials)

def save_to_firestore(user_id, data):
    """Lưu dữ liệu huấn luyện vào Firestore."""
    try:
        db = _get_firestore_client()
        db.collection("users").document(str(user_id)).collection("trained_data").add(data)
        logger.info(f"Saved data to Firestore for user {user_id}")
    except Exception as e:
        logger.error(f"Firestore save error for user {user_id}: {str(e)}")
        raise

def save_to_chat_history(user_id, query, response):
    """Lưu lịch sử chat vào Firestore."""
    try:
        db = _get_firestore_client()
        db.collection("users").document(str(user_id)).collection("chat_history").add({
            "user_message": query,
            "bot_response": response,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
        logger.info(f"Saved chat history for user {user_id}")
    except Exception as e:
        logger.error(f"Chat history save error for user {user_id}: {str(e)}")
        raise

def get_user_data(user_id):
    """Lấy dữ liệu huấn luyện của người dùng."""
    try:
        db = _get_firestore_client()
        docs = db.collection("users").document(str(user_id)).collection("trained_data").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(10).stream()
        data = [doc.to_dict() for doc in docs]
        logger.info(f"Retrieved {len(data)} records for user {user_id}")
        return data
    except Exception as e:
        logger.error(f"Firestore retrieve error for user {user_id}: {str(e)}")
        return []
