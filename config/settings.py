# File: /config/settings.py
from pydantic import BaseSettings, validator
import json

class Settings(BaseSettings):
    telegram_token: str
    gemini_api_key: str
    firestore_credentials: str

    @validator("firestore_credentials")
    def validate_credentials(cls, v):
        try:
            json.loads(v)
            return v
        except json.JSONDecodeError:
            raise ValueError("Invalid Firestore credentials JSON")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
