# Sử dụng Python 3.9 bản slim để nhẹ máy
FROM python:3.11-slim

# Cài đặt FFmpeg (Bắt buộc để yt-dlp xử lý video chất lượng cao)
# Update và cài đặt, sau đó xóa cache để giảm dung lượng image
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Thiết lập thư mục làm việc
WORKDIR /app

# Copy file requirements và cài đặt thư viện
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code vào
COPY . .

# Tạo user non-root để chạy cho an toàn (Best Practice)
RUN useradd -m appuser
USER appuser

# Mở port 5000
EXPOSE 5000

# Lệnh chạy ứng dụng với Gunicorn (4 workers cho khỏe)

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
