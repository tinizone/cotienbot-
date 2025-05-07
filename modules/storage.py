import os
import json
import logging
from google.oauth2.service_account import Credentials
from google.cloud import firestore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

_firestore_client = None

def _initialize_firestore():
    try:
        logger.info("Khởi tạo Firestore credentials...")
        credentials_path = os.path.join(os.path.dirname(__file__), "../credentials.json")
        if os.path.exists(credentials_path):
            logger.info("Sử dụng credentials từ file credentials.json")
            return Credentials.from_service_account_file(credentials_path)
        credentials_json = os.getenv("FIREBASE_CREDENTIALS")
        if credentials_json:
            logger.info("Sử dụng credentials từ biến môi trường FIREBASE_CREDENTIALS")
            credentials_dict = json.loads(credentials_json)
            return Credentials.from_service_account_info(credentials_dict)
        project_id = os.getenv("FIRESTORE_PROJECT_ID")
        if project_id:
            logger.info(f"Sử dụng project_id: {project_id} với IAM mặc định")
            return firestore.Client(project=project_id)
        raise ValueError("Không có thông tin xác thực Firestore hợp lệ.")
    except Exception as e:
        logger.error(f"Lỗi khởi tạo Firestore: {str(e)}")
        raise

def _get_firestore_client():
    global _firestore_client
    if _firestore_client is None:
        credentials = _initialize_firestore()
        if isinstance(credentials, firestore.Client):
            _firestore_client = credentials
        else:
            _firestore_client = firestore.Client(credentials=credentials)
    return _firestore_client

def save_to_firestore(user_id, data):
    try:
        user_id = str(user_id)
        if not user_id:
            logger.error(f"User ID không hợp lệ: {user_id}")
            raise ValueError("User ID không hợp lệ")
        if not data or not isinstance(data, dict):
            logger.error(f"Dữ liệu không hợp lệ cho user {user_id}: {data}")
            raise ValueError("Dữ liệu không hợp lệ")
        db = _get_firestore_client()
        data_with_timestamp = {
            **data,
            "timestamp": firestore.SERVER_TIMESTAMP
        }
        logger.debug(f"Dữ liệu sẽ lưu cho user {user_id}: {data_with_timestamp}")
        doc_ref = db.collection("users").document(user_id).collection("trained_data").add(data_with_timestamp)
        logger.info(f"Đã lưu dữ liệu huấn luyện cho user {user_id}, doc_id: {doc_ref[1].id}")
    except Exception as e:
        logger.error(f"Lỗi khi lưu dữ liệu user {user_id}: {str(e)}", exc_info=True)
        raise

def save_to_chat_history(user_id, query, response):
    try:
        user_id = str(user_id)
        db = _get_firestore_client()
        db.collection("users").document(user_id).collection("chat_history").add({
            "user_message": query,
            "bot_response": response,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
        logger.info(f"Đã lưu lịch sử chat cho user {user_id}")
    except Exception as e:
        logger.error(f"Lỗi khi lưu lịch sử chat user {user_id}: {str(e)}")
        raise

def get_user_data(user_id):
    try:
        user_id = str(user_id)
        db = _get_firestore_client()
        docs = db.collection("users").document(user_id).collection("trained_data") \
                 .order_by("timestamp", direction=firestore.Query.DESCENDING).limit(10).stream()
        data = [doc.to_dict() for doc in docs]
        logger.info(f"Lấy {len(data)} bản ghi từ Firestore cho user {user_id}")
        return data
    except Exception as e:
        logger.error(f"Lỗi khi lấy dữ liệu user {user_id}: {str(e)}")
        return []
