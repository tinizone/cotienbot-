# UPDATE: Dockerfile
FROM python:3.11-slim

# Cài dependencies cần thiết
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Nâng cấp pip và cài đặt phụ thuộc
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép mã nguồn
COPY . .

# Expose cổng mặc định của Render (dùng 10000 làm giá trị tượng trưng)
EXPOSE 10000

# Chạy ứng dụng với uvicorn, dùng shell form để biến $PORT được thay thế
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
