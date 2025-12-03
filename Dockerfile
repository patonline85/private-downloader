# Dùng Python 3.11
FROM python:3.11-slim

# 1. Cài FFmpeg, NodeJS (để giải mã JS) và GIT (để tải mã nguồn mới nhất)
RUN apt-get update && \
    apt-get install -y ffmpeg nodejs npm git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements nhưng CHƯA chạy vội
COPY requirements.txt .

# 2. Cài các thư viện phụ trước (Flask, gunicorn...)
RUN pip install --no-cache-dir Flask gunicorn

# 3. QUAN TRỌNG NHẤT: Cài yt-dlp trực tiếp từ Source Code trên GitHub (Bản Master)
# Lệnh này đảm bảo bạn luôn có bản vá lỗi mới nhất từng phút
RUN pip install --no-cache-dir --force-reinstall https://github.com/yt-dlp/yt-dlp/archive/master.zip

COPY . .

# Chạy quyền Root
USER root

EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "600", "app:app"]
