from pydantic_settings import BaseSettings
from pydantic import validator
import json

class Settings(BaseSettings):
    telegram_token: str
    gemini_api_key: str
    firestore_credentials: str
    render_domain: str  # Ví dụ: your-service.onrender.com
    admin_user_id: str  # Thêm admin_user_id để khắc phục lỗi AttributeError

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
