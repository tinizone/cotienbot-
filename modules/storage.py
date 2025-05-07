# Đường dẫn: cotienbot/modules/storage.py
# Tên file: storage.py

from google.cloud import firestore
import os

db = firestore.Client(project=os.getenv("FIRESTORE_PROJECT_ID"))

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
