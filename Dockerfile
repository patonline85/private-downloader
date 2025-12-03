# Dùng Python 3.11 bản đầy đủ
FROM python:3.11-bookworm

# 1. Cài đặt các công cụ hệ thống & FFmpeg
RUN apt-get update && \
    apt-get install -y curl gnupg git ffmpeg && \
    apt-get clean

# 2. Cài đặt NodeJS v20 (Cách chính thống dùng setup script)
# Lệnh này tự động cấu hình mọi thứ, không cần ln -s thủ công
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs

# 3. Cài đặt App
WORKDIR /app
# Cài các thư viện Python
RUN pip install --no-cache-dir Flask gunicorn
# Cài yt-dlp bản mới nhất từ Master (quan trọng)
RUN pip install --no-cache-dir --force-reinstall git+https://github.com/yt-dlp/yt-dlp.git@master

COPY . .

# Chạy quyền Root
USER root
EXPOSE 5000

# Timeout 10 phút, worker chạy 4 luồng
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "600", "app:app"]
