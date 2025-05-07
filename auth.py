import os
import logging
from google.cloud import firestore
from modules.storage import _get_firestore_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def authenticate_user(user_id, password):
    """Xác thực người dùng bằng mật khẩu."""
    try:
        user_id = str(user_id)
        correct_password = os.getenv("BOT_PASSWORD")
        if not correct_password:
            logger.error("BOT_PASSWORD is not set")
            return False, "Lỗi hệ thống: Mật khẩu bot chưa được thiết lập."

        if password != correct_password:
            logger.warning(f"Wrong password attempt for user {user_id}")
            return False, "Mật khẩu không đúng. Vui lòng thử lại."

        # Lưu trạng thái xác thực vào Firestore
        db = _get_firestore_client()
        db.collection("users").document(user_id).set({
            "is_authenticated": True,
            "timestamp": firestore.SERVER_TIMESTAMP
        }, merge=True)
        logger.info(f"User {user_id} authenticated successfully")
        return True, "Xác thực thành công! Bạn có thể sử dụng bot."

    except Exception as e:
        logger.error(f"Error authenticating user {user_id}: {str(e)}")
        return False, f"Lỗi khi xác thực: {str(e)}"

def check_authentication(user_id):
    """Kiểm tra trạng thái xác thực của người dùng."""
    try:
        user_id = str(user_id)
        db = _get_firestore_client()
        doc = db.collection("users").document(user_id).get()
        if doc.exists and doc.to_dict().get("is_authenticated", False):
            logger.info(f"User {user_id} is authenticated")
            return True
        logger.warning(f"User {user_id} is not authenticated")
        return False
    except Exception as e:
        logger.error(f"Error checking authentication for user {user_id}: {str(e)}")
        return False
