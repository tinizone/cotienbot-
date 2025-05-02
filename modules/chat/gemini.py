# File: /modules/chat/gemini.py
from google.generativeai import GenerativeModel, configure
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

def get_gemini_response(message: str) -> str:
    try:
        # Cấu hình API key
        configure(api_key=settings.gemini_api_key)
        
        # Kiểm tra danh sách model (debug)
        from google.api_core import exceptions
        from google.generativeai import list_models
        models = list_models()
        logger.info(f"Available models: {[model.name for model in models]}")
        
        # Sử dụng model mới nhất (có thể thay đổi dựa trên list_models)
        model_name = "gemini-2.0-flash"  # Cập nhật tên model, kiểm tra từ list_models
        model = GenerativeModel(model_name)
        
        response = model.generate_content(message)
        return response.text if hasattr(response, "text") else "No response from Gemini AI"
    except exceptions.NotFound as e:
        return f"Error with Gemini AI: 404 {str(e)}. Check available models with ListModels."
    except Exception as e:
        return f"Error with Gemini AI: {str(e)}"
