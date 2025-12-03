# Dùng Python 3.11 Bookworm (Debian 12)
FROM python:3.11-bookworm

# 1. Cài đặt NodeJS v20 chuẩn từ NodeSource
RUN apt-get update && \
    apt-get install -y curl gnupg git ffmpeg && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y nodejs && \
    apt-get clean

# 2. --- BÀN TAY SẮT: XỬ LÝ XUNG ĐỘT TÊN GỌI ---
# Xóa file /usr/bin/node cũ (nếu là cái node fake)
# Tạo link cứng từ nodejs sang node để không bao giờ nhầm nữa
RUN rm -f /usr/bin/node && \
    ln -s /usr/bin/nodejs /usr/bin/node

# 3. Setup Python
WORKDIR /app
RUN pip install --no-cache-dir Flask gunicorn
RUN pip install --no-cache-dir --force-reinstall git+https://github.com/yt-dlp/yt-dlp.git@master

COPY . .
USER root
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "600", "app:app"]
