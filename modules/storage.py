# Đường dẫn: cotienbot/modules/storage.py
# Tên file: storage.py

import os
import json
from google.cloud import firestore
from google.oauth2.service_account import Credentials

def initialize_firestore():
    """Khởi tạo Firestore client với credentials."""
    try:
        # Cách 1: Dùng file credentials.json (cho local hoặc Render.com nếu có file)
        credentials_path = os.path.join(os.path.dirname(__file__), "../credentials.json")
        if os.path.exists(credentials_path):
            credentials = Credentials.from_service_account_file(credentials_path)
            return firestore.Client(credentials=credentials)
        
        # Cách 2: Dùng biến môi trường FIREBASE_CREDENTIALS (cho Render.com)
        credentials_json = os.getenv("FIREBASE_CREDENTIALS")
        if credentials_json:
            credentials_dict = json.loads(credentials_json)
            credentials = Credentials.from_service_account_info(credentials_dict)
            return firestore.Client(credentials=credentials)
        
        # Fallback: Dùng project_id nếu không có credentials (cho môi trường tự xác thực)
        project_id = os.getenv("FIRESTORE_PROJECT_ID")
        if project_id:
            return firestore.Client(project=project_id)
        
        raise ValueError("Không tìm thấy credentials hoặc project_id để khởi tạo Firestore.")
    
    except Exception as e:
        print(f"Firestore initialization error: {str(e)}")
        raise

# Khởi tạo Firestore client
db = initialize_firestore()

def save_to_firestore(user_id, data):
    """Lưu dữ liệu huấn luyện vào Firestore."""
    try:
        db.collection("users").document(str(user_id)).collection("trained_data").add(data)
    except Exception as e:
        print(f"Firestore save error: {str(e)}")

def save_to_chat_history(user_id, query, response):
    """Lưu lịch sử chat vào Firestore."""
    try:
        db.collection("users").document(str(user_id)).collection("chat_history").add({
            "user_message": query,
            "bot_response": response,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        print(f"Chat history save error: {str(e)}")

def get_user_data(user_id):
    """Lấy dữ liệu huấn luyện của người dùng."""
    try:
        docs = db.collection("users").document(str(user_id)).collection("trained_data").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(10).stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        print(f"Firestore retrieve error: {str(e)}")
        return []
