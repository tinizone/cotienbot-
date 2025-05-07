# Đường dẫn: cotienbot/main.py
# Tên file: main.py

from flask import Flask, request
import telegram
import os
import logging
import signal
from modules.trainer import handle_train
from modules.retriever import retrieve_data
from modules.responder import generate_response
from utils.cleaner import clean_input

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
bot = telegram.Bot(token=os.getenv("TELEGRAM_TOKEN"))
processed_messages = set()  # Lưu message_id đã xử lý

@app.route("/", methods=["GET"])
def home():
    """Trả về thông tin bot khi truy cập root."""
    logger.info("Root endpoint called")
    return "Cotienbot webhook server. Use Telegram to interact.", 200

@app.route("/webhook", methods=["GET"])
def webhook_get():
    """Xử lý yêu cầu GET đến /webhook (không hỗ trợ)."""
    logger.info("Webhook GET endpoint called")
    return "Method GET not allowed. Use POST for Telegram webhook.", 405

@app.route("/webhook", methods=["POST"])
def webhook():
    """Xử lý tin nhắn từ Telegram qua webhook."""
    try:
        update = telegram.Update.de_json(request.get_json(force=True), bot)
        if not update.message:
            logger.info("Received empty message")
            return "OK", 200

        chat_id = update.message.chat_id
        message_id = update.message.message_id
        text = clean_input(update.message.text or "")
        logger.info(f"Received message from {chat_id}, message_id: {message_id}, text: {text}")

        # Kiểm tra tin nhắn trùng lặp
        if message_id in processed_messages:
            logger.info(f"Duplicate message_id {message_id}, skipping")
            return "OK", 200
        processed_messages.add(message_id)
        # Xóa message_id cũ để tránh bộ nhớ đầy (giữ tối đa 1000)
        if len(processed_messages) > 1000:
            processed_messages.pop()

        # Xử lý lệnh /start
        if text == "/start":
            response = "Chào mừng bạn đến với Cotienbot! Dùng /train text=... hoặc /train url=... để huấn luyện bot. Gửi câu hỏi bất kỳ để nhận phản hồi."
            bot.send_message(chat_id=chat_id, text=response)
            logger.info(f"Sent /start response to {chat_id}")
            return "OK", 200

        # Xử lý lệnh /help
        if text == "/help":
            response = "Hướng dẫn sử dụng Cotienbot:\n- /train text=...: Huấn luyện bot với văn bản.\n- /train url=...: Huấn luyện bot với nội dung từ URL.\n- Gửi câu hỏi để nhận phản hồi."
            bot.send_message(chat_id=chat_id, text=response)
            logger.info(f"Sent /help response to {chat_id}")
            return "OK", 200

        # Xử lý tin nhắn thông thường
        simple_greetings = ["hi", "hello", "chào", "xin chào"]
        if text.lower() in simple_greetings:
            response = "Chào bạn! Bạn khỏe không? Gửi câu hỏi hoặc dùng /train để huấn luyện bot nhé!"
            bot.send_message(chat_id=chat_id, text=response)
            logger.info(f"Sent greeting response to {chat_id}")
            return "OK", 200

        # Xử lý lệnh /train
        if text.startswith("/train"):
            response = handle_train(chat_id, text)
        else:
            # Xử lý hội thoại thông thường
            data = retrieve_data(chat_id, text)
            response = generate_response(chat_id, text, data)

        bot.send_message(chat_id=chat_id, text=response)
        logger.info(f"Sent response to {chat_id}: {response}")
        return "OK", 200
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return "Error", 500

@app.route("/health", methods=["GET"])
def health():
    """Health check để giữ instance Render.com chạy."""
    logger.info("Health check called")
    return "OK", 200

def handle_shutdown(signum, frame):
    """Ghi log khi server shutdown."""
    logger.info(f"Received signal {signum}, shutting down")
    raise SystemExit

if __name__ == "__main__":
    # Xử lý tín hiệu shutdown
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    
    port = int(os.getenv("PORT", 10000))
    logger.info(f"Starting server on port {port}")
    app.run(host="0.0.0.0", port=port)
