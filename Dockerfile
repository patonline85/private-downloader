FROM python:3.11-slim

# Cài FFmpeg và Node.js (BẮT BUỘC CHO YOUTUBE MỚI)
RUN apt-get update && \
    apt-get install -y ffmpeg nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

USER root
EXPOSE 5000

# Lệnh chạy: QUAN TRỌNG LÀ SỐ '-w 1'
# Ta dùng 1 Worker nhưng 4 Threads để tránh lỗi "Task not found"
CMD ["gunicorn", "-w", "1", "--threads", "4", "-b", "0.0.0.0:5000", "--timeout", "0", "app:app"]
