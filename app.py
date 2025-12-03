import os
import glob
from flask import Flask, render_template_string, request, send_file
from yt_dlp import YoutubeDL

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Pro Downloader</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, sans-serif; background: #f0f2f5; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .container { background: white; padding: 30px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); width: 90%; max-width: 450px; }
        h2 { text-align: center; color: #333; margin-bottom: 20px; }
        .input-group { margin-bottom: 15px; }
        input { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; font-size: 16px; }
        select { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 8px; background: white; font-size: 16px; }
        button { background: #007aff; color: white; border: none; padding: 15px; border-radius: 8px; cursor: pointer; font-weight: bold; width: 100%; font-size: 16px; margin-top: 10px; }
        button:hover { background: #005bb5; }
        .note { font-size: 12px; color: #888; margin-top: 20px; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🚀 Tải Video (Tên Gốc)</h2>
        <form method="POST" action="/download" onsubmit="document.getElementById('btn').innerText='⏳ Đang xử lý...'; document.getElementById('btn').disabled=true;">
            <div class="input-group">
                <input type="text" name="url" placeholder="Dán link Facebook/TikTok/Youtube..." required>
            </div>
            <div class="input-group">
                <select name="mode">
                    <option value="original">⚡ Mặc định (Tốt nhất + Tên gốc)</option>
                    <option value="mp4_convert">🍎 iPhone Chuẩn (MP4 1080p)</option>
                    <option value="audio_only">🎵 Chỉ lấy Nhạc (MP3)</option>
                </select>
            </div>
            <button type="submit" id="btn">Tải Về Ngay</button>
        </form>
        <p class="note">Hỗ trợ: Tiếng Việt, Emoji, Tên file chuẩn.</p>
    </div>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/download', methods=['POST'])
def download_video():
    url = request.form.get('url')
    mode = request.form.get('mode')
    
    # 1. Dọn dẹp file cũ
    old_files = glob.glob('/tmp/*')
    for f in old_files:
        try: os.remove(f)
        except: pass

    # Cấu hình
    ydl_opts = {
        # --- CẤU HÌNH TÊN FILE (QUAN TRỌNG) ---
        # 1. Lưu đúng tên Title của video
        # 2. Thêm ID phía sau để tránh trùng lặp nếu tên giống nhau
        'outtmpl': '/tmp/%(title)s [%(id)s].%(ext)s',
        
        # 3. QUAN TRỌNG: Cho phép ký tự Tiếng Việt và Unicode (Không lọc bỏ nữa)
        'restrictfilenames': False,
        
        # 4. Cắt ngắn tên file nếu quá dài (Facebook caption hay bị dài quá 255 ký tự gây lỗi)
        'trim_file_name': 200,
        # --------------------------------------

        'noplaylist': True,
        'cookiefile': 'cookies.txt',
        'ffmpeg_location': '/usr/bin/ffmpeg',
        'cachedir': False,
        'quiet': True,
        'extractor_args': {'youtube': {'player_client': ['web']}},
    }

    # Logic chọn chất lượng
    if mode == 'mp4_convert':
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'merge_output_format': 'mp4',
        })
    elif mode == 'audio_only':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}],
        })
    else: # Mặc định
        ydl_opts.update({
            # Lấy bản đẹp nhất, tự động merge nếu cần
            'format': 'bestvideo+bestaudio/best',
            # Nếu video là mkv/webm (Youtube), giữ nguyên để không tốn CPU convert
            # Nếu video là mp4 (Facebook/TikTok), giữ nguyên
            'merge_output_format': 'mp4', 
        })

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
            
        # Tìm file vừa tải
        list_of_files = glob.glob('/tmp/*')
        # Lọc bỏ cookies.txt
        files_video = [f for f in list_of_files if not f.endswith('.txt') and not f.endswith('.part')]
        
        if not files_video:
            return "❌ Lỗi: Không tìm thấy file. Link có thể là Private hoặc bị chặn.", 500
            
        # Lấy file mới nhất
        latest_file = max(files_video, key=os.path.getctime)
        
        # Gửi file về trình duyệt
        # as_attachment=True sẽ kích hoạt hộp thoại tải xuống
        # Flask tự động lấy tên file từ đường dẫn (đã có tiếng Việt) để gửi cho browser
        return send_file(latest_file, as_attachment=True)

    except Exception as e:
        return f"<h3>❌ Lỗi: {str(e)}</h3><button onclick='history.back()'>Quay lại</button>", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
