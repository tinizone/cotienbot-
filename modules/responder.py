# Đường dẫn: cotienbot/modules/responder.py
# Tên file: responder.py

import os
import requests
from modules.storage import save_to_chat_history

def generate_response(user_id, query, data):
    """Tạo phản hồi dựa trên dữ liệu hoặc Gemini AI."""
    try:
        if data:
            response = f"Dựa trên thông tin bạn cung cấp: {data['content'][:200]}..."
            save_to_chat_history(user_id, query, response)
            return response
        
        # Gọi Gemini AI nếu không có dữ liệu
        gemini_url = "https://api.gemini.ai/v1/generate"  # Giả lập, thay bằng URL thật
        headers = {"Authorization": f"Bearer {os.getenv('GEMINI_API_KEY')}"}
        payload = {
            "prompt": query,
            "context": f"User ID: {user_id}\nInstruction: Answer naturally in Vietnamese.",
            "max_tokens": 200
        }
        
        response = requests.post(gemini_url, json=payload, headers=headers, timeout=5)
        if response.status_code == 200:
            text = response.json().get("text", "Không có phản hồi từ Gemini.")
            full_response = f"[Gemini] {text}"
            save_to_chat_history(user_id, query, full_response)
            return full_response
        
        fallback = "Không thể tạo phản hồi từ Gemini, vui lòng thử lại sau."
        save_to_chat_history(user_id, query, fallback)
        return fallback
    
    except Exception as e:
        error_msg = f"Lỗi khi tạo phản hồi: {str(e)}"
        save_to_chat_history(user_id, query, error_msg)
        return error_msg
