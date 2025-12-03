# Dùng Python trên nền Debian 12 (Bookworm) bản FULL để tránh thiếu thư viện
FROM python:3.11-bookworm

# 1. Cài đặt các công cụ hệ thống căn bản
RUN apt-get update && \
    apt-get install -y curl gnupg git ffmpeg && \
    apt-get clean

# 2. Cài đặt NodeJS v20 (Bản mới nhất) - QUAN TRỌNG NHẤT
# Lệnh này sẽ tải repo của NodeSource về để cài bản xịn, không dùng bản cũ của Debian
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y nodejs

# 3. Kiểm tra version ngay trong lúc build để chắc chắn đã cài được
RUN node -v && npm -v

# 4. Thiết lập thư mục
WORKDIR /app

# 5. Cài các thư viện Python
RUN pip install --no-cache-dir Flask gunicorn

# 6. Cài yt-dlp từ Source Master (GitHub) để có bản vá lỗi mới nhất
# Lưu ý: Lệnh này dùng git để kéo code mới nhất về
RUN pip install --no-cache-dir --force-reinstall git+https://github.com/yt-dlp/yt-dlp.git@master

# 7. Copy code vào
COPY . .

# Chạy quyền Root để tránh mọi lỗi về quyền hạn file
USER root

EXPOSE 5000

# Tăng timeout lên 10 phút
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "600", "app:app"]
