# Đường dẫn: cotienbot/main.py
# Tên file: main.py

from flask import Flask, request
import telegram
import os
import logging
import signal

# Trì hoãn import các module khác để tránh circular import
def import_modules():
    global handle_train, retrieve_data, generate_response, clean_input
    from modules.trainer import handle_train
    from modules.retriever import retrieve_data
    from modules.responder import generate_response
    from utils.cleaner import clean_input

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
bot = telegram.Bot(token=os.getenv("TELEGRAM_TOKEN"))

# Import modules khi cần
import_modules()

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
        text = clean_input(update.message.text or "")
        logger.info(f"Received message from {chat_id}: {text}")

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

        # Xử lý lệnh /train
        if text.startswith("/train"):
            if "text=" in text or "url=" in text:
                response = handle_train(chat_id, text)
            else:
                response = "Sai cú pháp. Vui lòng dùng /train text=... hoặc /train url=.... Ví dụ: /train text=Tôi tên Vinh"
                logger.info(f"Invalid /train syntax from {chat_id}: {text}")
            bot.send_message(chat_id=chat_id, text=response)
            return "OK", 200

        # Xử lý hội thoại thông thường
        data = retrieve_data(chat_id, text)
        if not data and not text.startswith("/"):
            response = generate_response(chat_id, text, data)
            # Gợi ý huấn luyện nếu không có dữ liệu
            if response.startswith("[Gemini]"):
                response += "\n(Hiện tại tôi chưa có dữ liệu huấn luyện. Dùng /train để cung cấp thông tin nhé!)"
        else:
            response = generate_response(chat_id, text, data)

        bot.send_message(chat_id=chat_id, text=response)
        logger.info(f"Sent response to {chat_id}: {response}")
        return "OK", 200

    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        bot.send_message(chat_id=chat_id, text="Đã xảy ra lỗi, vui lòng thử lại sau.")
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
