# File: /modules/default_data.py
import logging
import google.generativeai as genai
import json
import os
from config.settings import settings
from sentence_transformers import SentenceTransformer
from telegram.ext import CommandHandler
from telegram import Update
from telegram.ext import CallbackContext
from database.firestore import FirestoreClient
import numpy as np
import faiss

logger = logging.getLogger(__name__)

# Cấu hình Gemini API
genai.configure(api_key=settings.gemini_api_key)
gemini_model = None

def get_gemini_model():
    global gemini_model
    if gemini_model is None:
        logger.info("Đang khởi tạo mô hình Gemini...")
        gemini_model = genai.GenerativeModel("gemini-1.5-flash")
    return gemini_model

# Khởi tạo SentenceTransformer
sentence_model = None

def get_sentence_model():
    global sentence_model
    if sentence_model is None:
        logger.info("Đang tải mô hình Sentence Transformers...")
        sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
    return sentence_model

# Sinh 500 câu hội thoại (chạy cục bộ)
def generate_conversations(num_conversations=500):
    conversations = []
    gemini = get_gemini_model()
    for i in range(num_conversations):
        try:
            prompt = (
                "Sinh một cặp câu hỏi và trả lời thông dụng cho trợ lý ảo, ví dụ: "
                "Hỏi: 'Bạn tên là gì?' Trả lời: 'Tôi là trợ lý ảo.' "
                "Trả về định dạng: Hỏi: <câu hỏi> Trả lời: <câu trả lời>"
            )
            response = gemini.generate_content(prompt).text
            if "Hỏi:" in response and "Trả lời:" in response:
                question, answer = response.split("Trả lời:", 1)
                question = question.replace("Hỏi:", "").strip()
                answer = answer.strip()
                conversations.append({"question": question, "answer": answer})
            else:
                logger.warning(f"Định dạng không đúng cho câu {i+1}: {response}")
        except Exception as e:
            logger.error(f"Lỗi khi sinh câu thứ {i+1}: {str(e)}")
    return conversations

# Lưu vào file JSON (chạy cục bộ)
def save_to_json(conversations, filename="default_conversations.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(conversations, f, ensure_ascii=False, indent=2)
    logger.info(f"Đã lưu {len(conversations)} câu hội thoại vào {filename}")

# Cấu hình dữ liệu mẫu trong RAM
default_data_cache = {}
default_data_embeddings = {}
faiss_index = None
faiss_questions = None
_cache = {}

def load_from_json_and_save_to_firestore(filename="default_conversations.json"):
    global default_data_cache, default_data_embeddings, faiss_index, faiss_questions
    if not os.path.exists(filename):
        logger.error(f"File {filename} không tồn tại")
        return
    with open(filename, "r", encoding="utf-8") as f:
        conversations = json.load(f)
    db = FirestoreClient()
    sentence_model = get_sentence_model()
    group_size = 50
    for i in range(0, len(conversations), group_size):
        group = conversations[i:i + group_size]
        group_data = []
        for conv in group:
            question = conv["question"]
            answer = conv["answer"]
            embedding = sentence_model.encode(question).tolist()
            group_data.append({
                "question": question,
                "answer": answer
            })
            default_data_cache[question] = answer
            default_data_embeddings[question] = embedding
        doc_ref = db.client.collection("default_training_data").document(f"group_{i // group_size}")
        doc_ref.set({
            "conversations": group_data,
            "timestamp": db.SERVER_TIMESTAMP
        })
        logger.info(f"Đã lưu nhóm {i // group_size}: {len(group)} câu")
    # Khởi tạo Faiss index
    dimension = 192  # Kích thước vector của all-MiniLM-L6-v2
    index = faiss.IndexFlatL2(dimension)
    questions = list(default_data_embeddings.keys())
    embeddings = np.array([default_data_embeddings[q] for q in questions], dtype=np.float32)
    index.add(embeddings)
    faiss_index = index
    faiss_questions = questions

def find_default_answer(user_id: str, message: str) -> str | None:
    try:
        global faiss_index, faiss_questions
        if not faiss_index or not faiss_questions:
            logger.info("Dữ liệu mẫu chưa được khởi tạo")
            return None

        cache_key = f"{user_id}:{message}"
        if cache_key in _cache:
            logger.info(f"Trả lời từ cache cho user {user_id}: {_cache[cache_key]}")
            return _cache[cache_key]

        db = FirestoreClient()
        query_embedding = np.array([db._get_embedding(message)], dtype=np.float32)
        distances, indices = faiss_index.search(query_embedding, k=1)
        if distances[0][0] < 0.6:
            question = faiss_questions[indices[0][0]]
            best_match = default_data_cache[question]
            db.save_chat(user_id, message, best_match)
            _cache[cache_key] = best_match
            logger.info(f"Trả lời từ dữ liệu mẫu cho user {user_id}: {best_match}")
            return best_match
        return None
    except Exception as e:
        logger.error(f"Lỗi khi tìm dữ liệu mẫu: {str(e)}")
        return None

# Lệnh để khởi tạo dữ liệu mẫu (dùng thủ công)
async def init_default_data(update: Update, context: CallbackContext) -> None:
    try:
        logger.info("Bắt đầu khởi tạo dữ liệu mẫu...")
        await update.message.reply_text("Đang khởi tạo dữ liệu mẫu, vui lòng chờ...")
        conversations = generate_conversations(500)
        save_to_json(conversations)
        load_from_json_and_save_to_firestore()
        await update.message.reply_text("Đã khởi tạo xong 500 câu hội thoại mẫu!")
    except Exception as e:
        logger.error(f"Lỗi khi khởi tạo dữ liệu mẫu: {str(e)}")
        await update.message.reply_text("Có lỗi xảy ra khi khởi tạo dữ liệu mẫu.")

def register_handlers():
    return [
        CommandHandler("initdefaultdata", init_default_data)
    ]

# Chạy cục bộ để sinh dữ liệu (không chạy trên Render)
if __name__ == "__main__":
    conversations = generate_conversations(500)
    save_to_json(conversations)
    load_from_json_and_save_to_firestore()
