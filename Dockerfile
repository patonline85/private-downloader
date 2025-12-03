# Dùng bản Python Bookworm (Debian 12) đầy đủ, không dùng slim để tránh thiếu thư viện
FROM python:3.11-bookworm

# 1. Cài đặt các công cụ hệ thống cần thiết
RUN apt-get update && \
    apt-get install -y curl gnupg git ffmpeg && \
    apt-get clean

# 2. Cài đặt NodeJS v20 (Bản mới nhất để giải mã Youtube n-challenge)
# Đây là bước quan trọng nhất mà bản cũ bị thiếu
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y nodejs

# 3. Tạo thư mục làm việc
WORKDIR /app

# 4. Cài thư viện Python cơ bản
RUN pip install --no-cache-dir Flask gunicorn

# 5. Cài yt-dlp từ Source Master (Để có bản vá lỗi PO Token mới nhất)
RUN pip install --no-cache-dir --force-reinstall https://github.com/yt-dlp/yt-dlp/archive/master.zip

# 6. Copy code vào
COPY . .

# Chạy quyền Root để tránh lỗi permission
USER root

EXPOSE 5000

# Timeout dài để tải 4K
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "600", "app:app"]
