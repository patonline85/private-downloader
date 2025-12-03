# Sử dụng Python 3.11 trên nền Debian 12 (Bookworm)
FROM python:3.11-bookworm

# 1. Cài đặt các công cụ hệ thống
RUN apt-get update && \
    apt-get install -y curl gnupg git ffmpeg && \
    apt-get clean

# 2. Cài đặt NodeJS v20 (Tự động hóa bước bạn đã làm tay)
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y nodejs

# 3. FIX LỖI "SYMLINK" & TÊN GỌI (Codify bước sửa nóng của bạn)
# Xóa file node cũ nếu có và tạo link cứng mới để đảm bảo /usr/bin/node luôn tồn tại
RUN rm -f /usr/bin/node && \
    ln -s /usr/bin/nodejs /usr/bin/node

# 4. Kiểm tra luôn trong quá trình Build (Nếu không ra version, Build sẽ thất bại ngay)
RUN node -v && npm -v

# 5. Cài đặt App
WORKDIR /app
RUN pip install --no-cache-dir Flask gunicorn
# Cài bản Master của yt-dlp để có code mới nhất
RUN pip install --no-cache-dir --force-reinstall git+https://github.com/yt-dlp/yt-dlp.git@master

COPY . .

# Chạy quyền Root
USER root
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "600", "app:app"]
