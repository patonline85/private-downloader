# Dùng Python 3.11
FROM python:3.11-slim

# Cài FFmpeg VÀ NodeJS (Chìa khóa để fix lỗi)
RUN apt-get update && \
    apt-get install -y ffmpeg nodejs npm && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Chạy quyền Root
USER root

EXPOSE 5000

# Timeout 10 phút
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "600", "app:app"]
