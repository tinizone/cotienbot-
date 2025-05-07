# Đường dẫn: cotienbot/modules/retriever.py
# Tên file: retriever.py

from modules.storage import get_user_data
from utils.cleaner import clean_input

def retrieve_data(user_id, query):
    """Tìm dữ liệu huấn luyện phù hợp với câu hỏi."""
    try:
        cleaned_query = clean_input(query).lower()
        data = get_user_data(user_id)
        
        # Tìm kiếm đơn giản: so sánh từ khóa
        for item in data:
            content = item["content"].lower()
            if cleaned_query in content or any(word in content for word in cleaned_query.split()):
                return item
        
        return None  # Không tìm thấy dữ liệu phù hợp
    
    except Exception as e:
        print(f"Retriever error: {str(e)}")
        return None
