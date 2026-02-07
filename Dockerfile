# Dùng Python 3.11 Slim
FROM python:3.11-slim

# Cài FFmpeg và dọn dẹp cache để giảm dung lượng ảnh
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cài thư viện Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir --upgrade yt-dlp
    
# Copy mã nguồn
COPY . .

# Chạy quyền Root (để xử lý file tạm và cookies)
USER root

EXPOSE 5000

# Timeout 600s = 10 phút (Cho video dài)
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "--timeout", "600", "app:app"]

