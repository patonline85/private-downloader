import os
import glob
from flask import Flask, render_template_string, request, send_file
from yt_dlp import YoutubeDL

app = Flask(__name__)

# Giao diện HTML đơn giản (Clean UI)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Private Downloader</title>
    <style>
        body { font-family: -apple-system, sans-serif; background: #f0f2f5; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .container { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); width: 100%; max-width: 400px; text-align: center; }
        input { width: 90%; padding: 12px; margin-bottom: 20px; border: 1px solid #ddd; border-radius: 8px; }
        button { background: #007aff; color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; font-weight: bold; width: 100%; }
        button:hover { background: #005bb5; }
        .note { font-size: 12px; color: #666; margin-top: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🚀 Private Downloader</h2>
        <form method="POST" action="/download">
            <input type="text" name="url" placeholder="Dán link Facebook/Youtube vào đây..." required>
            <button type="submit">Tải Video Ngay</button>
        </form>
        <p class="note">Support: Facebook, Youtube, TikTok (No Watermark)</p>
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
    
    # Cấu hình yt-dlp
    # Lưu ý: Render dùng hệ file tạm, ta lưu vào /tmp
    ydl_opts = {
        'outtmpl': '/tmp/%(title)s.%(ext)s',
        'format': 'best', # Tải chất lượng tốt nhất (đã merge video+audio nếu có ffmpeg)
        'noplaylist': True,
    }

    try:
        # Dọn dẹp file cũ trong /tmp trước khi tải mới (tránh đầy bộ nhớ)
        files = glob.glob('/tmp/*')
        for f in files:
            try:
                os.remove(f)
            except: pass

        # Thực hiện tải video về Server
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info_dict)
        
        # Gửi file về client
        return send_file(filename, as_attachment=True)

    except Exception as e:
        return f"Lỗi: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)