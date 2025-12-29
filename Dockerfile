FROM python:3.11-slim

# 1. Cài đặt FFmpeg, Node.js và các thư viện cần thiết
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    nodejs \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Copy file requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. [QUAN TRỌNG] Ép cập nhật yt-dlp lên bản mới nhất (Bleeding Edge)
# Vì bản trên PyPI đôi khi cập nhật chậm hơn thuật toán YouTube
RUN pip install --no-cache-dir -U "https://github.com/yt-dlp/yt-dlp/archive/master.zip"

COPY . .

USER root
EXPOSE 5000

# 4. Chạy Gunicorn với 1 worker để tránh lỗi Task not found
CMD ["gunicorn", "-w", "1", "--threads", "4", "-b", "0.0.0.0:5000", "--timeout", "0", "app:app"]
