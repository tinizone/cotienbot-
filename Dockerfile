# File: /Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Nâng cấp pip và cài đặt phụ thuộc
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install --no-cache-dir --root-user-action=ignore -r requirements.txt

# Sao chép mã nguồn
COPY . .

# Expose cổng mặc định của Render
EXPOSE 10000

# Chạy ứng dụng với uvicorn, sử dụng main.py ở root
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
