import google.generativeai as genai
from config.settings import settings

genai.configure(api_key=settings.gemini_api_key)

def get_gemini_response(message: str) -> str:
    model = genai.GenerativeModel("gemini-pro")
    response = model.generate_content(message)
    return response.text
