# Đường dẫn: cotienbot/utils/cleaner.py
# Tên file: cleaner.py

import re

def clean_input(text):
    """Làm sạch văn bản đầu vào."""
    if not text:
        return ""
    
    # Loại bỏ ký tự đặc biệt, emoji, khoảng trắng dư
    text = re.sub(r"[^\w\s.,!?]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    
    # Chuẩn hóa chữ thường (tùy chọn, có thể bỏ nếu cần giữ nguyên)
    text = text.lower()
    
    return text
