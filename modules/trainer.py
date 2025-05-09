import re
import requests
from bs4 import BeautifulSoup
import logging

def _import_firestore():
    global firestore
    import google.cloud.firestore as firestore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def handle_train(user_id, command):
    """Xử lý lệnh /train để lưu dữ liệu huấn luyện."""
    logger.info(f"Processing /train command for user {user_id}: {command}")
    _import_firestore()
    
    command = command.strip()
    if not command.startswith("/"):
        command = "/" + command
    
    try:
        if "text=" in command:
            content = command.split("text=", 1)[1].strip()
        elif command.startswith("/train text "):
            content = command[len("/train text "):].strip()
        else:
            content = None
        
        if content:
            if not content:
                logger.warning(f"Empty content for /train text from user {user_id}")
                return "Vui lòng cung cấp nội dung văn bản."
            cleaned_content = clean_input(content)
            if not isinstance(cleaned_content, str) or not cleaned_content:
                logger.error(f"Dữ liệu không hợp lệ cho user {user_id}: {cleaned_content}")
                return "Nội dung không hợp lệ."
            if len(cleaned_content) > 5000:
                logger.warning(f"Content too long for user {user_id}: {len(cleaned_content)} chars")
                return "Nội dung quá dài, tối đa 5000 ký tự."
            data = {
                "content": cleaned_content,
                "type": "text",
                "timestamp": firestore.SERVER_TIMESTAMP
            }
            logger.debug(f"Chuẩn bị lưu dữ liệu cho user {user_id}: {data}")
            save_to_firestore(user_id, data)
            logger.info(f"Saved text training data for user {user_id}: {cleaned_content[:50]}...")
            return f"Dữ liệu văn bản đã được lưu: {cleaned_content[:50]}..."

        elif "url=" in command:
            url = command.split("url=", 1)[1].strip()
            if not re.match(r"https?://", url):
                logger.warning(f"Invalid URL from user {user_id}: {url}")
                return "URL không hợp lệ, vui lòng bắt đầu bằng http:// hoặc https://."
            try:
                response = requests.get(url, timeout=10)
                if response.status_code != 200:
                    logger.error(f"Failed to access URL for user {user_id}: {url}, status {response.status_code}")
                    return f"Không thể truy cập URL: {url}"
                soup = BeautifulSoup(response.text, "html.parser")
                for tag in soup(["script", "style", "header", "footer", "nav"]):
                    tag.decompose()
                content = soup.get_text(separator=" ", strip=True)
                cleaned_content = clean_input(content)
                if not isinstance(cleaned_content, str) or not cleaned_content:
                    logger.error(f"Dữ liệu không hợp lệ cho user {user_id}: {cleaned_content}")
                    return "Nội dung không hợp lệ."
                if len(cleaned_content) > 5000:
                    logger.warning(f"URL content too long for user {user_id}: {len(cleaned_content)} chars")
                    return "Nội dung URL quá dài, tối đa 5000 ký tự."
                data = {
                    "content": cleaned_content,
                    "type": "url",
                    "source": url,
                    "timestamp": firestore.SERVER_TIMESTAMP
                }
                logger.debug(f"Chuẩn bị lưu dữ liệu cho user {user_id}: {data}")
                save_to_firestore(user_id, data)
                logger.info(f"Saved URL training data for user {user_id}: {url}")
                return f"Dữ liệu từ {url} đã được lưu."
            except requests.RequestException as e:
                logger.error(f"URL request error for user {user_id}: {str(e)}")
                return f"Lỗi khi truy cập URL: {str(e)}"

        else:
            logger.warning(f"Invalid /train syntax from user {user_id}: {command}")
            return "Sai định dạng. Vui lòng dùng /train text=... hoặc /train url=.... Ví dụ: /train text=Tôi tên Vinh"

    except Exception as e:
        logger.error(f"Error handling /train for user {user_id}: {str(e)}", exc_info=True)
        return f"Lỗi khi xử lý lệnh /train: {str(e)}"

def save_to_firestore(user_id, data):
    from modules.storage import save_to_firestore
    save_to_firestore(user_id, data)

def clean_input(text):
    from utils.cleaner import clean_input
    return clean_input(text)
