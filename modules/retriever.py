# Đường dẫn: cotienbot/modules/retriever.py
# Tên file: retriever.py
from modules.storage import get_user_data
from utils.cleaner import clean_input
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

def retrieve_data(user_id, query):
    """Tìm dữ liệu huấn luyện phù hợp với câu hỏi."""
    try:
        cleaned_query = clean_input(query).lower()
        data = get_user_data(user_id)
        
        if not data:
            logger.info(f"No training data found for user {user_id}")
            return None
        
        query_words = cleaned_query.split()
        for item in data:
            content = item.get("content", "").lower()
            if any(word in content for word in query_words):
                logger.info(f"Found matching record for user {user_id}, query: {query}")
                return item
        
        logger.info(f"No matching data found for user {user_id}, query: {query}")
        return None
    
    except Exception as e:
        logger.error(f"Retriever error: {str(e)}")
        return None
