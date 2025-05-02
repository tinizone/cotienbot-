# File: /modules/chat/gemini.py
import google.generativeai as genai
from config.settings import settings

genai.configure(api_key=settings.gemini_api_key)

def get_gemini_response(message: str) -> str:
    try:
        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(message)
        return response.text if hasattr(response, "text") else "No response from Gemini AI"
    except Exception as e:
        return f"Error with Gemini AI: {str(e)}"
