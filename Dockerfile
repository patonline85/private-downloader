FROM python:3.11-slim

# Tắt hỏi đáp khi cài đặt
ENV DEBIAN_FRONTEND=noninteractive

# Cập nhật và cài đặt:
# 1. ffmpeg: để ghép video + audio
# 2. nodejs: để yt-dlp giải mã thuật toán YouTube (Fix lỗi Warning JS Runtime)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

USER root
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
