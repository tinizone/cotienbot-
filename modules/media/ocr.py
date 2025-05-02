from modules.chat.gemini import get_gemini_response

def extract_text_from_image(image_content: bytes):
    prompt = "Extract text from this image."
    # Gemini hiện không hỗ trợ xử lý ảnh trực tiếp qua API đơn giản
    # Dùng placeholder, sẽ tích hợp Tesseract sau
    return get_gemini_response(prompt)
