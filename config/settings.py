from pydantic import BaseSettings

class Settings(BaseSettings):
    telegram_token: str
    gemini_api_key: str
    firestore_credentials: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
