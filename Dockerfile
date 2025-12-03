# Dùng Python 3.11 mới hơn để yt-dlp chạy mượt
FROM python:3.11-slim

# Cài FFmpeg
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Chạy với quyền Root để tránh lỗi Permission file cookies (như đã bàn)
USER root

EXPOSE 5000

# Tăng timeout lên 600s (10 phút) để tải video dài không bị ngắt
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "600", "app:app"]
