# Đường dẫn: cotienbot/modules/retriever.py
# Tên file: retriever.py
from modules.storage import get_user_data
from utils.cleaner import clean_input
from sentence_transformers import SentenceTransformer, util
from cachetools import TTLCache
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Khởi tạo mô hình SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')

# Khởi tạo cache với TTL = 300 giây (5 phút) và tối đa 100 user
cache = TTLCache(maxsize=100, ttl=300)

def retrieve_data(user_id, query):
    """Tìm dữ liệu huấn luyện phù hợp với câu hỏi bằng semantic search."""
    try:
        cleaned_query = clean_input(query)
        user_id = str(user_id)
        
        # Kiểm tra cache
        cache_key = f"{user_id}_data"
        cached_data = cache.get(cache_key)
        
        if cached_data is None:
            # Lấy dữ liệu từ Firestore nếu không có trong cache
            data = get_user_data(user_id)
            if not data:
                logger.info(f"No training data found for user {user_id}")
                return None
            
            # Nhúng tất cả nội dung dữ liệu và lưu vào cache
            embeddings = []
            for item in data:
                content = item.get("content", "")
                embedding = model.encode(content, convert_to_tensor=True)
                embeddings.append(embedding)
            cached_data = {"data": data, "embeddings": embeddings}
            cache[cache_key] = cached_data
            logger.info(f"Cached data for user {user_id}, {len(data)} records")
        else:
            logger.info(f"Using cached data for user {user_id}")
            data = cached_data["data"]
            embeddings = cached_data["embeddings"]
        
        # Nhúng câu hỏi
        query_embedding = model.encode(cleaned_query, convert_to_tensor=True)
        
        best_match = None
        best_score = -1  # Cosine similarity từ -1 đến 1
        
        # Tìm bản ghi có mức độ tương đồng cao nhất
        for item, embedding in zip(data, embeddings):
            score = util.cos_sim(query_embedding, embedding).item()
            if score > best_score:
                best_score = score
                best_match = item
        
        # Chỉ trả về nếu mức độ tương đồng đủ cao (> 0.5)
        if best_score > 0.5:
            logger.info(f"Found matching record for user {user_id}, query: {query}, similarity: {best_score}")
            return best_match
        
        logger.info(f"No sufficiently relevant data found for user {user_id}, query: {query}")
        return None
    
    except Exception as e:
        logger.error(f"Retriever error: {str(e)}")
        return None
