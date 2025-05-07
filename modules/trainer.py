# Đường dẫn: cotienbot/modules/trainer.py
# Tên file: trainer.py

import re
import requests
from bs4 import BeautifulSoup
from utils.cleaner import clean_input
from modules.storage import save_to_firestore

def handle_train(user_id, command):
    """Xử lý lệnh /train để lưu dữ liệu huấn luyện."""
    try:
        if "text=" in command:
            content = command.split("text=", 1)[1].strip()
            if not content:
                return "Vui lòng cung cấp nội dung văn bản."
            cleaned_content = clean_input(content)
            if len(cleaned_content) > 5000:
                return "Nội dung quá dài, tối đa 5000 ký tự."
            save_to_firestore(user_id, {
                "content": cleaned_content,
                "type": "text",
                "timestamp": firestore.SERVER_TIMESTAMP
            })
            return "Dữ liệu văn bản đã được lưu."

        elif "url=" in command:
            url = command.split("url=", 1)[1].strip()
            if not re.match(r"https?://", url):
                return "URL không hợp lệ, vui lòng bắt đầu bằng http:// hoặc https://."
            
            try:
                response = requests.get(url, timeout=5)
                if response.status_code != 200:
                    return f"Không thể truy cập URL: {url}"
                
                soup = BeautifulSoup(response.text, "html.parser")
                # Lấy nội dung chính, bỏ thẻ không cần thiết
                for tag in soup(["script", "style", "header", "footer", "nav"]):
                    tag.decompose()
                content = soup.get_text(separator=" ", strip=True)
                
                cleaned_content = clean_input(content)
                if len(cleaned_content) > 5000:
                    return "Nội dung URL quá dài, tối đa 5000 ký tự."
                
                save_to_firestore(user_id, {
                    "content": cleaned_content,
                    "type": "url",
                    "source": url,
                    "timestamp": firestore.SERVER_TIMESTAMP
                })
                return f"Dữ liệu từ {url} đã được lưu."
            
            except requests.RequestException as e:
                return f"Lỗi khi truy cập URL: {str(e)}"

        else:
            return "Sai định dạng. Vui lòng dùng /train text=... hoặc /train url=..."
    
    except Exception as e:
        return f"Lỗi khi xử lý lệnh /train: {str(e)}"
