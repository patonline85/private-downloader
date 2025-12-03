import os
import glob
from flask import Flask, render_template_string, request, send_file
from yt_dlp import YoutubeDL

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Super Downloader</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, sans-serif; background: #222; color: #fff; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .container { background: #333; padding: 30px; border-radius: 16px; width: 90%; max-width: 450px; }
        input, select, button { width: 100%; padding: 15px; margin-bottom: 15px; border-radius: 8px; border: none; font-size: 16px; }
        button { background: #0a84ff; color: white; font-weight: bold; cursor: pointer; }
        button:hover { background: #0077e6; }
        .badge { background: #444; padding: 5px 10px; border-radius: 4px; font-size: 12px; color: #aaa; }
    </style>
</head>
<body>
    <div class="container">
        <h2 style="text-align:center">🚀 4K Downloader</h2>
        <form method="POST" action="/download">
            <input type="text" name="url" placeholder="Paste Link Youtube/FB/TikTok..." required>
            
            <label>Chọn chất lượng:</label>
            <select name="mode">
                <option value="max_res">🌟 4K/2K Gốc (MKV) - Nét nhất (Cần VLC)</option>
                <option value="safe_mp4">📱 1080p/720p (MP4) - Tương thích mọi iPhone</option>
                <option value="audio">🎵 Nhạc (MP3)</option>
            </select>

            <button type="submit" onclick="this.innerText='⏳ Server đang tải...'">Tải Ngay</button>
        </form>
        <p class="badge">Core: yt-dlp | Server: Armbian</p>
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
    
    # Dọn dẹp file cũ
    for f in glob.glob('/tmp/*'):
        try: os.remove(f)
        except: pass

    # Cấu hình cốt lõi
    ydl_opts = {
        'outtmpl': '/tmp/video_download.%(ext)s',
        'noplaylist': True,
        'cookiefile': 'cookies.txt',
        'ffmpeg_location': '/usr/bin/ffmpeg',
        'quiet': False,
        # Giả lập Android để lấy được luồng 4K ngon nhất
        'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36'}
    }

    # --- LOGIC CHỌN FILE ---
    
    if mode == 'max_res':
        # CHẾ ĐỘ 4K (Dựa trên log của bạn: ID 313/401 + Audio)
        ydl_opts.update({
            # Lấy Video tốt nhất (bất kể codec) + Audio tốt nhất
            'format': 'bestvideo+bestaudio/best',
            # Gói vào MKV (Container này chứa được mọi loại codec 4K mà không cần convert)
            'merge_output_format': 'mkv', 
        })
        
    elif mode == 'safe_mp4':
        # CHẾ ĐỘ IPHONE (Chỉ lấy tối đa 1080p để đảm bảo là MP4 hịn)
        ydl_opts.update({
            # Lấy video MP4 tốt nhất (thường là 1080p ID 137 hoặc 720p) + Audio M4A
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'merge_output_format': 'mp4',
        })
        
    elif mode == 'audio':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}],
        })

    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
            
        # Tìm file vừa tải
        list_of_files = glob.glob('/tmp/*')
        # Lọc bỏ cookies.txt ra khỏi danh sách tìm kiếm
        files_video = [f for f in list_of_files if not f.endswith('.txt')]
        
        if not files_video:
            return "❌ Lỗi: Server tải xong nhưng không thấy file.", 500
            
        latest_file = max(files_video, key=os.path.getctime)
        return send_file(latest_file, as_attachment=True)

    except Exception as e:
        return f"<h3>❌ Lỗi: {str(e)}</h3><button onclick='history.back()'>Quay lại</button>", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
