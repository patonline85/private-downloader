import os
import glob
import shutil
from flask import Flask, render_template_string, request, send_file
from yt_dlp import YoutubeDL

app = Flask(__name__)

# Giao diện đơn giản, tập trung vào tính năng
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Safe Downloader</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, sans-serif; background: #f2f2f7; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .card { background: white; padding: 30px; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); width: 90%; max-width: 400px; text-align: center; }
        h2 { margin-top: 0; color: #1c1c1e; }
        input { width: 100%; padding: 14px; margin-bottom: 15px; border: 1px solid #d1d1d6; border-radius: 10px; box-sizing: border-box; font-size: 16px; }
        button { width: 100%; padding: 14px; background: #007aff; color: white; border: none; border-radius: 10px; font-weight: bold; font-size: 16px; cursor: pointer; }
        button:disabled { background: #8e8e93; }
        .note { font-size: 12px; color: #8e8e93; margin-top: 15px; }
    </style>
</head>
<body>
    <div class="card">
        <h2>📥 Tải Video An Toàn</h2>
        <form method="POST" action="/download" onsubmit="document.getElementById('btn').disabled=true; document.getElementById('btn').innerText='⏳ Đang xử lý (Vui lòng đợi)...'">
            <input type="text" name="url" placeholder="Dán link Youtube/Facebook..." required>
            <button type="submit" id="btn">Tải Về Ngay</button>
        </form>
        <p class="note">Server sẽ tự chọn chất lượng tốt nhất (MP4) cho iPhone.</p>
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/download', methods=['POST'])
def download_video():
    url = request.form['url']
    
    # 1. Dọn dẹp file rác
    for f in glob.glob('/tmp/*'):
        try: os.remove(f)
        except: pass

    # 2. Cấu hình yt-dlp "An Toàn Nhất"
    ydl_opts = {
        'outtmpl': '/tmp/%(title)s.%(ext)s',
        'restrictfilenames': True, # Tên file an toàn (không dấu)
        'noplaylist': True,
        'cookiefile': 'cookies.txt',
        'ffmpeg_location': '/usr/bin/ffmpeg',
        'quiet': True,
        
        # --- CHIẾN THUẬT AUTO-BEST ---
        # Ưu tiên 1: Video MP4 (H.264) + Audio M4A (Tốt nhất cho iPhone)
        # Ưu tiên 2: Bất kỳ Video nào + Bất kỳ Audio nào (Merge lại thành MP4)
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        
        # --- FIX LỖI MÔI TRƯỜNG ---
        'extractor_args': {'youtube': {'player_client': ['web']}}, # Dùng Web Client ổn định
        'cachedir': False, # Tắt cache để tránh lỗi Node cũ
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
            
        # Tìm file kết quả
        files = [f for f in glob.glob('/tmp/*') if not f.endswith('.txt') and not f.endswith('.part')]
        
        if not files:
            return "<h3>❌ Lỗi: Server tải xong nhưng không thấy file. Kiểm tra lại Link hoặc Cookies.</h3><a href='/'>Quay lại</a>", 500
            
        # Lấy file mới nhất
        latest_file = max(files, key=os.path.getctime)
        return send_file(latest_file, as_attachment=True)

    except Exception as e:
        return f"<h3>❌ Có lỗi xảy ra:</h3><pre>{str(e)}</pre><a href='/'>Quay lại</a>", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
