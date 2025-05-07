# Đường dẫn: cotienbot/modules/responder.py
# Tên file: responder.py

import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from modules.storage import save_to_chat_history

def generate_response(user_id, query, data):
    """Tạo phản hồi dựa trên dữ liệu hoặc Gemini-2.0-Flash."""
    try:
        if data:
            response = f"Dựa trên thông tin bạn cung cấp: {data['content'][:200]}..."
            save_to_chat_history(user_id, query, response)
            return response
        
        # Cấu hình retry cho requests
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retries))

        # Gọi Gemini-2.0-Flash API
        gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        headers = {
            "Authorization": f"Bearer {os.getenv('GEMINI_API_KEY')}",
            "Content-Type": "application/json"
        }
        payload = {
            "contents": [{
                "parts": [{
                    "text": f"User ID: {user_id}\nQuery: {query}\nInstruction: Answer naturally in Vietnamese."
                }]
            }],
            "generationConfig": {
                "maxOutputTokens": 200
            }
        }
        
        response = session.post(gemini_url, json=payload, headers=headers, timeout=5)
        if response.status_code == 200:
            text = response.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "Không có phản hồi từ Gemini.")
            full_response = f"[Gemini] {text}"
            save_to_chat_history(user_id, query, full_response)
            return full_response
        
        error_msg = f"Gemini API error: {response.status_code} - {response.text}"
        save_to_chat_history(user_id, query, error_msg)
        return error_msg
    
    except requests.exceptions.RequestException as e:
        error_msg = f"Lỗi khi gọi Gemini API: {str(e)}"
        save_to_chat_history(user_id, query, error_msg)
        return error_msg
