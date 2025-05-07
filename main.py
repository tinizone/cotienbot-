from flask import Flask, request
import telegram
import os
import logging
import signal
import requests
from collections import deque
from modules.trainer import handle_train
from modules.retriever import retrieve_data
from modules.responder import generate_response
from utils.cleaner import clean_input
import time

# Thiết lập logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
bot = telegram.Bot(token=os.getenv("TELEGRAM_TOKEN"))

# Giới hạn bộ nhớ tin nhắn đã xử lý
MAX_PROCESSED = 1000
processed_messages = deque(maxlen=MAX_PROCESSED)  # chứa các cặp (chat_id, message_id)

def set_webhook():
    """Tự động cài đặt webhook khi server khởi động."""
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    webhook_url = os.getenv("WEBHOOK_URL")
    
    if not webhook_url:
        logger.error("WEBHOOK_URL environment variable is not set")
        return
    
    url = f"https://api.telegram.org/bot{telegram_token}/setWebhook"
    payload = {"url": webhook_url}
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            logger.info("Webhook set successfully: %s", response.json())
        else:
            logger.error("Failed to set webhook: %s", response.text)
    except Exception as e:
        logger.error("Error setting webhook: %s", str(e))

@app.route("/", methods=["GET"])
def home():
    logger.info("Root endpoint called")
    return "Cotienbot webhook server. Use Telegram to interact.", 200

@app.route("/webhook", methods=["GET"])
def webhook_get():
    logger.info("Webhook GET endpoint called")
    return "Method GET not allowed. Use POST for Telegram webhook.", 405

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        update = telegram.Update.de_json(request.get_json(force=True), bot)
        if not update.message:
            logger.info("Received empty message")
            return "OK", 200

        chat_id = update.message.chat_id
        message_id = update.message.message_id
        message_key = (chat_id, message_id)

        text = clean_input(update.message.text or "")
        logger.info(f"Received message from {chat_id}, message_id: {message_id}, text: {text}")

        if message_key in processed_messages:
            logger.info(f"Duplicate message {message_key}, skipping")
            return "OK", 200
        processed_messages.append(message_key)

        if text == "/start":
            response = (
                "Chào mừng bạn đến với Cotienbot! Dùng /train text=... hoặc /train url=... để huấn luyện bot. "
                "Gửi câu hỏi bất kỳ để nhận phản hồi."
            )
            send_with_retry(chat_id, response)
            return "OK", 200

        if text == "/help":
            response = (
                "Hướng dẫn sử dụng Cotienbot:\n"
                "- /train text=...: Huấn luyện bot với văn bản.\n"
                "- /train url=...: Huấn luyện bot với nội dung từ URL.\n"
                "- Gửi câu hỏi để nhận phản hồi."
            )
            send_with_retry(chat_id, response)
            return "OK", 200

        if text.lower() in ["hi", "hello", "chào", "xin chào"]:
            response = "Chào bạn! Bạn khỏe không? Gửi câu hỏi hoặc dùng /train để huấn luyện bot nhé!"
            send_with_retry(chat_id, response)
            return "OK", 200

        # Xử lý lệnh huấn luyện hoặc phản hồi
        if text.startswith("/train"):
            response = handle_train(chat_id, text)
        else:
            data = retrieve_data(chat_id, text)
            response = generate_response(chat_id, text, data)

        send_with_retry(chat_id, response)
        return "OK", 200

    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return "Error", 500

@app.route("/health", methods=["GET"])
def health():
    logger.info("Health check called")
    return "OK", 200

def send_with_retry(chat_id, text, retries=3, delay=1):
    """Gửi tin nhắn với retry nếu gặp lỗi tạm thời."""
    for attempt in range(retries):
        try:
            bot.send_message(chat_id=chat_id, text=text)
            return
        except Exception as e:
            logger.warning(f"Gửi tin nhắn lỗi (attempt {attempt+1}): {e}")
            time.sleep(delay)
    logger.error(f"Thất bại khi gửi tin nhắn sau {retries} lần.")

def handle_shutdown(signum, frame):
    logger.info(f"Received signal {signum}, shutting down")
    raise SystemExit

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    
    # Tự động cài đặt webhook khi server khởi động
    set_webhook()
    
    port = int(os.getenv("PORT", 10000))
    logger.info(f"Starting server on port {port}")
    app.run(host="0.0.0.0", port=port)
