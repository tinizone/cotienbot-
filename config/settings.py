# File: /config/settings.py
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    telegram_token: str = os.getenv("TELEGRAM_TOKEN", "")
    render_domain: str = os.getenv("RENDER_DOMAIN", "")
    firestore_credentials: str = os.getenv("FIRESTORE_CREDENTIALS", "{}")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
