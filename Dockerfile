# Sử dụng Python 3.11 Slim
FROM python:3.11-slim

# Cài đặt FFmpeg (Bắt buộc cho việc ghép video chất lượng cao)
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy và cài đặt thư viện
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn
COPY . .

# Chạy với quyền Root (như yêu cầu cũ)
USER root

# Expose port 8000 (Mặc định của Uvicorn/FastAPI)
EXPOSE 8000

# Lệnh chạy server bằng Uvicorn (FastAPI)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
