FROM python:3.11-slim

# Tắt hỏi đáp khi cài đặt
ENV DEBIAN_FRONTEND=noninteractive

# Cài FFmpeg nhẹ nhàng
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

USER root
EXPOSE 8000

# Lệnh chạy quan trọng: main:app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
