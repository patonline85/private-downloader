import os
import glob
import json
import time
import subprocess
import shutil
from flask import Flask, render_template_string, request, send_file, Response, stream_with_context
from yt_dlp import YoutubeDL

app = Flask(__name__)

# --- CẤU HÌNH MÔI TRƯỜNG ---
# Đảm bảo Python nhìn thấy NodeJS (Fix lỗi n-challenge)
if '/usr/bin' not in os.environ['PATH']:
    os.environ['PATH'] = '/usr/bin:' + os.environ['PATH']

# --- GIAO DIỆN HTML + JAVASCRIPT ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Pro Downloader</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, sans-serif; background: #1c1c1e; color: #fff; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .container { background: #2c2c2e; padding: 30px; border-radius: 16px; width: 90%; max-width: 450px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        h2 { text-align: center; margin-bottom: 20px; color: #fff; }
        
        input { width: 100%; padding: 15px; margin-bottom: 20px; border-radius: 8px; border: 1px solid #3a3a3c; background: #1c1c1e; color: white; box-sizing: border-box; font-size: 16px; }
        input:focus { outline: none; border-color: #0a84ff; }
        
        button { width: 100%; padding: 15px; background: #30d158; color: white; border: none; font-weight: bold; border-radius: 8px; cursor: pointer; font-size: 16px; transition: 0.2s; }
        button:hover { background: #28b148; }
        button:disabled { background: #48484a; cursor: not-allowed; }

        /* THANH TIẾN TRÌNH */
        .progress-container { margin-top: 25px; display: none; }
        .progress-bg { width: 100%; background-color: #3a3a3c; border-radius: 10px; height: 12px; overflow: hidden; }
        .progress-bar { height: 100%; width: 0%; background-color: #0a84ff; transition: width 0.3s ease; }
        .status-text { text-align: center; margin-top: 10px; font-size: 0.9em; color: #aeaeb2; font-family: monospace; }
        
        /* LINK TẢI VỀ */
        #downloadArea { display: none; margin-top: 20px; text-align: center; }
        .save-btn { display: inline-block; padding: 12px 25px; background: #0a84ff; color: white; text-decoration: none; border-radius: 8px; font-weight: bold; }
        
        .error-msg { color: #ff453a; text-align: center; margin-top: 15px; display: none; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🚀 Server Downloader</h2>
        <form id="dlForm">
            <input type="text" id="url" placeholder="Dán link Youtube/Facebook..." required>
            <button type="submit" id="submitBtn">Bắt đầu Tải</button>
        </form>

        <div class="progress-container" id="progressArea">
            <div class="progress-bg">
                <div class="progress-bar" id="progressBar"></div>
            </div>
            <div class="status-text" id="statusText">Đang kết nối...</div>
        </div>

        <div id="downloadArea">
            <p>✅ Xử lý xong!</p>
            <a href="#" id="finalLink" class="save-btn">Lưu Video Về Máy</a>
        </div>
        
        <p id="errorText" class="error-msg"></p>
    </div>

    <script>
        document.getElementById('dlForm').onsubmit = async function(e) {
            e.preventDefault();
            const btn = document.getElementById('submitBtn');
            const progressArea = document.getElementById('progressArea');
            const progressBar = document.getElementById('progressBar');
            const statusText = document.getElementById('statusText');
            const downloadArea = document.getElementById('downloadArea');
            const errorText = document.getElementById('errorText');
            
            // Reset giao diện
            btn.disabled = true;
            downloadArea.style.display = 'none';
            errorText.style.display = 'none';
            progressArea.style.display = 'block';
            progressBar.style.width = '0%';
            statusText.innerText = 'Đang khởi động Server...';
            
            const formData = new FormData();
            formData.append('url', document.getElementById('url').value);

            try {
                // Gọi API Streaming
                const response = await fetch('/stream_download', { method: 'POST', body: formData });
                const reader = response.body.getReader();
                const decoder = new TextDecoder();

                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;
                    
                    // Xử lý dữ liệu stream trả về
                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\\n');
                    
                    for (const line of lines) {
                        if (!line.trim()) continue;
                        try {
                            const data = JSON.parse(line);
                            
                            if (data.status === 'downloading') {
                                // Cập nhật thanh tiến trình
                                progressBar.style.width = data.percent + '%';
                                statusText.innerText = `Đang tải: ${data.percent}% | Tốc độ: ${data.speed}`;
                            } else if (data.status === 'merging') {
                                // Giai đoạn ghép file (FFmpeg)
                                progressBar.style.width = '95%';
                                progressBar.style.backgroundColor = '#ffcc00'; // Màu vàng
                                statusText.innerText = 'Đang ghép file (Merge)... Vui lòng đợi!';
                            } else if (data.status === 'finished') {
                                // Hoàn tất
                                progressBar.style.width = '100%';
                                progressBar.style.backgroundColor = '#30d158'; // Màu xanh
                                statusText.innerText = 'Hoàn tất!';
                                document.getElementById('finalLink').href = '/get_file/' + encodeURIComponent(data.filename);
                                downloadArea.style.display = 'block';
                                btn.disabled = false;
                            } else if (data.status === 'error') {
                                throw new Error(data.message);
                            }
                        } catch (err) {
                            if (err.message) {
                                errorText.innerText = "Lỗi: " + err.message;
                                errorText.style.display = 'block';
                                progressArea.style.display = 'none';
                                btn.disabled = false;
                            }
                        }
                    }
                }
            } catch (error) {
                errorText.innerText = "Lỗi kết nối: " + error;
                errorText.style.display = 'block';
                btn.disabled = false;
            }
        };
    </script>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def index():
    return render_template_string(HTML_TEMPLATE)

# --- API STREAMING (CỐT LÕI CỦA THANH TIẾN TRÌNH) ---
@app.route('/stream_download', methods=['POST'])
def stream_download():
    url = request.form.get('url')

    def generate():
        # 1. Dọn dẹp
        for f in glob.glob('/tmp/*'):
            try: os.remove(f)
            except: pass

        # 2. Hàm Hook: Bắt lấy % tải về và gửi cho trình duyệt
        def progress_hook(d):
            if d['status'] == 'downloading':
                # Lấy số % (bỏ ký tự màu mè nếu có)
                p = d.get('_percent_str', '0%').replace('%','').strip()
                # Lấy tốc độ
                s = d.get('_speed_str', 'N/A')
                # Gửi về client dạng JSON (Stream)
                yield json.dumps({'status': 'downloading', 'percent': p, 'speed': s}) + "\n"
            elif d['status'] == 'finished':
                yield json.dumps({'status': 'merging'}) + "\n"

        ydl_opts = {
            'outtmpl': '/tmp/%(title)s.%(ext)s',
            'restrictfilenames': True,
            'cookiefile': 'cookies.txt',
            'ffmpeg_location': '/usr/bin/ffmpeg',
            'quiet': True,
            'progress_hooks': [progress_hook], # Gắn hàm theo dõi vào đây
            'extractor_args': {'youtube': {'player_client': ['web']}},
            
            # Cấu hình Auto-Best (Ưu tiên MP4 cho iPhone)
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
            
            'cachedir': False, # Tắt cache để tránh lỗi
        }

        try:
            # Bắt đầu tải
            with YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=True)
            
            # Tìm file kết quả
            files = [f for f in glob.glob('/tmp/*') if not f.endswith('.txt') and not f.endswith('.part')]
            if files:
                final_file = max(files, key=os.path.getctime)
                filename = os.path.basename(final_file)
                # Báo tín hiệu thành công kèm tên file
                yield json.dumps({'status': 'finished', 'filename': filename}) + "\n"
            else:
                yield json.dumps({'status': 'error', 'message': 'Không tìm thấy file sau khi tải'}) + "\n"

        except Exception as e:
            # Báo lỗi về giao diện
            yield json.dumps({'status': 'error', 'message': str(e)}) + "\n"

    # Trả về Response dạng Stream (text/plain) để JS đọc dần dần
    return Response(stream_with_context(generate()), mimetype='text/plain')

# API Tải file về máy (Sau khi server xử lý xong)
@app.route('/get_file/<filename>')
def get_file(filename):
    safe_path = os.path.join('/tmp', filename)
    if os.path.exists(safe_path):
        return send_file(safe_path, as_attachment=True)
    return "Not Found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
