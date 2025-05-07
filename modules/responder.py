# responder.py
import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
from modules.storage import save_to_chat_history

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def generate_response(user_id, query, data):
    """Tạo phản hồi dựa trên dữ liệu huấn luyện hoặc Gemini-1.5-Flash."""
    try:
        query_lower = query.lower()
        
        # Xử lý dữ liệu huấn luyện
        if data:
            content = data.get("content", "").lower()
            
            # Kiểm tra mức độ liên quan
            query_words = query_lower.split()
            content_words = content.split()
            common_words = set(query_words) & set(content_words)
            is_relevant = len(common_words) > 0  # Có ít nhất 1 từ khóa chung
            
            if is_relevant:
                # Xử lý câu hỏi về tên
                if "tên" in query_lower and "tên" in content:
                    name = content.split("tên")[-1].strip()
                    response = f"Bạn tên là {name}!"
                    save_to_chat_history(user_id, query, response)
                    logger.info(f"Generated name response for user {user_id}: {response}")
                    return response
                
                # Trả về dữ liệu huấn luyện nếu liên quan
                response = f"Dựa trên thông tin bạn cung cấp: {data['content'][:200]}..."
                save_to_chat_history(user_id, query, response)
                logger.info(f"Generated response from Firestore for user {user_id}")
                return response

        # Nếu không có dữ liệu hoặc dữ liệu không liên quan, gọi Gemini
        # Kiểm tra kết nối mạng
        try:
            test_response = requests.get("https://www.google.com", timeout=5)
            logger.info(f"Test connection to Google: {test_response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error: {str(e)}")
            error_msg = "Không thể kết nối đến mạng. Vui lòng kiểm tra kết nối của bạn."
            save_to_chat_history(user_id, query, error_msg)
            return error_msg

        # Kiểm tra GEMINI_API_KEY
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY is not set")
            response = "Tôi chưa có đủ thông tin để trả lời câu hỏi này. Bạn có thể dùng /train text=... hoặc /train url=... để dạy tôi nhé! Ví dụ: /train text=Nha Trang có nhiều bãi biển đẹp."
            save_to_chat_history(user_id, query, response)
            logger.info(f"Sent default response for user {user_id} due to missing API key")
            return response

        # Cấu hình retry cho requests
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retries))

        # Gọi Gemini-1.5-Flash API
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
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
        
        logger.info(f"Sending Gemini request for user {user_id}: {query}")
        response = session.post(gemini_url, json=payload, headers=headers, timeout=5)
        logger.info(f"Gemini response status: {response.status_code}, body: {response.text}")

        if response.status_code == 200:
            text = response.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "Không có phản hồi từ Gemini.")
            full_response = f"[Gemini] {text}"
            save_to_chat_history(user_id, query, full_response)
            return full_response
        
        error_msg = f"Lỗi Gemini API: {response.status_code} - {response.text}"
        logger.error(error_msg)
        save_to_chat_history(user_id, query, error_msg)
        return "Hệ thống AI tạm thời không khả dụng, vui lòng thử lại sau."

    except requests.exceptions.RequestException as e:
        error_msg = f"Hệ thống AI tạm thời không khả dụng do lỗi mạng: {str(e)}"
        logger.error(f"Gemini error: {str(e)}")
        save_to_chat_history(user_id, query, error_msg)
        return error_msg
