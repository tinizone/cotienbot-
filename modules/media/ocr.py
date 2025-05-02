# File: /modules/media/ocr.py
from PIL import Image
import pytesseract
import io

def extract_text_from_image(image_content: bytes) -> str:
    try:
        img = Image.open(io.BytesIO(image_content))
        text = pytesseract.image_to_string(img)
        return text if text else "No text found"
    except Exception as e:
        return f"Error processing image: {str(e)}"
