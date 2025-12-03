FROM python:3.11-bookworm

# 1. Cài đặt NodeJS v20 từ nguồn chính hãng NodeSource
# (Dùng script setup chuẩn để tránh lỗi)
RUN apt-get update && apt-get install -y curl gnupg git ffmpeg && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean

# 2. --- QUAN TRỌNG: Ép biến môi trường PATH ---
# Dòng này đảm bảo Gunicorn nhìn thấy /usr/bin/node
ENV PATH="/usr/bin:${PATH}"

# 3. Setup Ứng dụng
WORKDIR /app
RUN pip install --no-cache-dir Flask gunicorn
# Cài bản mới nhất của yt-dlp
RUN pip install --no-cache-dir --force-reinstall git+https://github.com/yt-dlp/yt-dlp.git@master

COPY . .

# Chạy quyền Root
USER root
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "600", "app:app"]
