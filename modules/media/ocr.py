async def process_photo(photo_data: bytes) -> str:
    from google.generativeai import GenerativeModel
    model = GenerativeModel(get_latest_model())
    response = model.generate_content(["Describe this image", photo_data])
    return response.text
