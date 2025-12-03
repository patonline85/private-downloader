# Dùng Python 3.11 Bookworm (Bản Full)
FROM python:3.11-bookworm

# 1. Cài đặt công cụ cơ bản
RUN apt-get update && \
    apt-get install -y curl gnupg git ffmpeg && \
    apt-get clean

# 2. Cài đặt NodeJS v20
# (Lưu ý: Không dùng lệnh ln -s thủ công nữa để tránh lỗi vòng lặp symlink)
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y nodejs

# 3. Setup App
WORKDIR /app
RUN pip install --no-cache-dir Flask gunicorn
# Cài bản Master yt-dlp mới nhất
RUN pip install --no-cache-dir --force-reinstall git+https://github.com/yt-dlp/yt-dlp.git@master

COPY . .

# Chạy quyền Root
USER root
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "600", "app:app"]
