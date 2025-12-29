# 
FROM python:3.11-slim

# Cài FFmpeg VÀ Node.js (Cần thiết cho yt-dlp giải mã signature của YouTube)
RUN apt-get update && \
    apt-get install -y ffmpeg nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

USER root

EXPOSE 5000

# Thêm tham số --threads 4 để xử lý request tốt hơn (thay vì chỉ dùng worker process)
CMD ["gunicorn", "-w", "4", "--threads", "4", "-b", "0.0.0.0:5000", "--timeout", "600", "app:app"]
