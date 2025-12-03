import os
import glob
from flask import Flask, render_template_string, request, send_file
from yt_dlp import YoutubeDL

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Armbian 4K Downloader</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: sans-serif; background: #1a1a1a; color: #fff; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .container { background: #2d2d2d; padding: 30px; border-radius: 12px; width: 90%; max-width: 500px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        input, select { width: 100%; padding: 15px; margin-bottom: 15px; background: #444; border: 1px solid #555; color: white; border-radius: 6px; box-sizing: border-box; }
        button { width: 100%; padding: 15px; background: #e50914; color: white; border: none; font-weight: bold; border-radius: 6px; cursor: pointer; font-size: 1.1em; }
        button:hover { background: #b2070f; }
    </style>
</head>
<body>
    <div class="container">
        <h2 style="text-align:center">SERVER DOWNLOADER</h2>
        <form method="POST" action="/download">
            <input type="text" name="url" placeholder="Dán link vào đây..." required>
            <select name="mode">
                <option value="4k_mkv">🌟 4K GỐC (MKV) - Giữ tên gốc & Chất lượng</option>
                <option value="iphone">📱 iPhone (MP4 1080p) - Convert (Lâu)</option>
                <option value="mp3">🎵 MP3 (Audio) - Tách nhạc</option>
            </select>
            <button type="submit" onclick="this.innerText='⏳ Đang xử lý... (Đừng tắt)'">TẢI VỀ</button>
        </form>
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
    
    # 1. Dọn dẹp file cũ trong /tmp
    # Rất quan trọng để tìm đúng file vừa tải
    for f in glob.glob('/tmp/*'):
        try: os.remove(f)
        except: pass

    # Cấu hình chung
    ydl_opts = {
        # Sửa lại: Dùng tên gốc của video (Title)
        'outtmpl': '/tmp/%(title)s.%(ext)s',
        'noplaylist': True,
        'cookiefile': 'cookies.txt',
        'ffmpeg_location': '/usr/bin/ffmpeg',
        'quiet': False,
        # Tăng kích thước buffer để tải 4K ổn định hơn
        'buffersize': 1024 * 1024, 
        'extractor_args': {'youtube': {'player_client': ['android', 'ios']}},
    }

    if mode == '4k_mkv':
        ydl_opts.update({
            # QUAN TRỌNG: Xóa bỏ "/best" để không bao giờ fallback về MP4 chất lượng thấp
            # Bắt buộc phải tìm được Video riêng và Audio riêng để ghép
            'format': 'bestvideo+bestaudio', 
            'merge_output_format': 'mkv' 
        })
    elif mode == 'iphone':
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'merge_output_format': 'mp4'
        })
    elif mode == 'mp3':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}]
        })

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
            
        # Tìm file vừa tải xong
        # Logic: Lấy tất cả file trong /tmp trừ cookies.txt
        files = [f for f in glob.glob('/tmp/*') if not f.endswith('.txt')]
        
        if not files:
            return "<h3>Lỗi: Không tìm thấy file tải về. Có thể Video này không có 4K hoặc bị Youtube chặn.</h3>", 500
        
        # Lấy file mới nhất (vừa được tạo ra)
        # Cách này đảm bảo lấy đúng file dù tên nó là gì
        latest_file = max(files, key=os.path.getctime)
        
        # Gửi file về với tên gốc
        return send_file(latest_file, as_attachment=True)

    except Exception as e:
        return f"""
        <h3>❌ Lỗi tải về:</h3>
        <p>{str(e)}</p>
        <p><i>Gợi ý: Nếu lỗi "Requested format is not available", nghĩa là video này không có định dạng 4K tách rời. Hãy thử chọn chế độ iPhone.</i></p>
        <button onclick="history.back()">Quay lại</button>
        """, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
