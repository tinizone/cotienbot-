# UPDATE: /modules/chat/gemini.py
from google.generativeai import GenerativeModel, configure
from google.api_core import exceptions
from config.settings import settings
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

def get_latest_model() -> str:
    """Get the latest Gemini model from available models."""
    from google.generativeai import list_models
    try:
        models = list_models()
        gemini_models = [model.name for model in models if "gemini" in model.name.lower()]
        logger.info(f"Available Gemini models: {gemini_models}")
        return gemini_models[0] if gemini_models else "gemini-1.5-flash"  # Fallback
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        return "gemini-1.5-flash"

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def get_gemini_response(message: str) -> str:
    """Generate a response using the latest Gemini model."""
    try:
        configure(api_key=settings.gemini_api_key)
        model_name = get_latest_model()
        model = GenerativeModel(model_name)
        response = model.generate_content(message)
        if not hasattr(response, "text"):
            logger.error(f"Invalid Gemini response: {response}")
            return "No valid response from Gemini AI"
        logger.info(f"Generated response with model {model_name}")
        return response.text
    except exceptions.NotFound as e:
        logger.error(f"Gemini model not found: {str(e)}")
        return f"Error: Model not found. Check available models."
    except exceptions.ResourceExhausted as e:
        logger.error(f"Gemini quota exceeded: {str(e)}")
        return "Error: API quota exceeded. Please try again later."
    except Exception as e:
        logger.error(f"Error with Gemini AI: {str(e)}")
        raise  # Let tenacity handle retries
