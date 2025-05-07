# Đường dẫn: cotienbot/main.py
# Tên file: main.py

from flask import Flask, request
import telegram
import os
from modules.trainer import handle_train
from modules.retriever import retrieve_data
from modules.responder import generate_response
from utils.cleaner import clean_input

app = Flask(__name__)
bot = telegram.Bot(token=os.getenv("TELEGRAM_TOKEN"))

@app.route("/webhook", methods=["POST"])
def webhook():
    """Xử lý tin nhắn từ Telegram qua webhook."""
    try:
        update = telegram.Update.de_json(request.get_json(force=True), bot)
        if not update.message:
            return "OK", 200

        chat_id = update.message.chat_id
        text = clean_input(update.message.text or "")

        if text.startswith("/train"):
            response = handle_train(chat_id, text)
        else:
            data = retrieve_data(chat_id, text)
            response = generate_response(chat_id, text, data)

        bot.send_message(chat_id=chat_id, text=response)
        return "OK", 200
    except Exception as e:
        print(f"Webhook error: {str(e)}")
        return "Error", 500

@app.route("/health", methods=["GET"])
def health():
    """Health check để giữ instance Render.com chạy."""
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
