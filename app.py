import os
import glob
from flask import Flask, render_template_string, request, send_file
from yt_dlp import YoutubeDL

app = Flask(__name__)

# Giao diện HTML nâng cấp với Menu chọn định dạng
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Pro Downloader @Armbian</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, sans-serif; background: #f0f2f5; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .container { background: white; padding: 30px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); width: 90%; max-width: 450px; }
        h2 { text-align: center; color: #333; margin-bottom: 20px; }
        .input-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: 600; color: #555; font-size: 0.9em; }
        input[type="text"] { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; font-size: 16px; }
        select { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 8px; background: white; font-size: 16px; appearance: none; }
        button { background: #007aff; color: white; border: none; padding: 15px; border-radius: 8px; cursor: pointer; font-weight: bold; width: 100%; font-size: 16px; margin-top: 10px; transition: 0.2s; }
        button:hover { background: #005bb5; }
        .note { font-size: 12px; color: #888; margin-top: 20px; text-align: center; line-height: 1.5; }
        .badge { background: #eee; padding: 2px 6px; border-radius: 4px; font-family: monospace; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🚀 Server Downloader</h2>
        <form method="POST" action="/download">
            
            <div class="input-group">
                <label>Dán Link Video (Youtube/FB/TikTok):</label>
                <input type="text" name="url" placeholder="https://..." required>
            </div>

            <div class="input-group">
                <label>Chọn Chế Độ Tải:</label>
                <select name="mode">
                    <option value="original">⚡ Gốc (4K/MKV) - Nhanh nhất (Cần VLC)</option>
                    <option value="mp4_convert">🍎 iPhone Chuẩn (MP4) - Tốn CPU Convert</option>
                    <option value="audio_only">🎵 Chỉ lấy Audio (MP3)</option>
                </select>
            </div>

            <button type="submit" onclick="this.innerText='⏳ Đang xử lý trên Server...'">Tải Về Ngay</button>
        </form>
        <p class="note">
            • <b>Gốc:</b> Giữ nguyên chất lượng 4K/8K. iPhone cần cài app VLC/Infuse để xem.<br>
            • <b>iPhone Chuẩn:</b> Server sẽ convert về H.264. Xem được ngay trong Photos nhưng chờ lâu.<br>
            • Server: Armbian | Engine: yt-dlp + ffmpeg
        </p>
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
    mode = request.form.get('mode') # Lấy chế độ người dùng chọn
    
    # Cấu hình chung cơ bản
    ydl_opts = {
        'outtmpl': '/tmp/%(title)s.%(ext)s',
        'noplaylist': True,
        'cookiefile': 'cookies.txt',
        'ffmpeg_location': '/usr/bin/ffmpeg', # Đường dẫn FFmpeg chuẩn trên Docker
        'cachedir': False,
        'quiet': False,
        
        # Giả lập Client để tránh lỗi 403
        'extractor_args': {
            'youtube': {
                'player_client': ['android_creator', 'web'],
                'player_skip': ['webpage', 'configs', 'js'],
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
    }

    # --- XỬ LÝ LOGIC THEO LỰA CHỌN ---
    
    if mode == 'mp4_convert':
        # Chế độ tương thích iPhone (Tốn CPU)
        ydl_opts.update({
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
        })
        
    elif mode == 'audio_only':
        # Chế độ tách nhạc MP3
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
        
    else: # mode == 'original' (Mặc định)
        # Chế độ tải file gốc (Nhanh nhất, giữ 4K)
        # Chỉ merge video + audio vào container MKV/WebM chứ KHÔNG convert lại codec
        ydl_opts.update({
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mkv', # MKV là container an toàn nhất cho mọi codec
        })

    try:
        # Dọn dẹp file cũ
        files = glob.glob('/tmp/*')
        for f in files:
            try: os.remove(f)
            except: pass

        # Thực thi
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info_dict)
            
            # Xử lý phần mở rộng file sau khi convert (đặc biệt cho MP3)
            if mode == 'audio_only':
                base, _ = os.path.splitext(filename)
                filename = base + ".mp3"
            elif mode == 'mp4_convert':
                base, _ = os.path.splitext(filename)
                filename = base + ".mp4"
            elif mode == 'original':
                # Đôi khi merge xong nó ra .mkv
                base, _ = os.path.splitext(filename)
                filename = base + ".mkv"

        return send_file(filename, as_attachment=True)

    except Exception as e:
        return f"""
        <h3>❌ Có lỗi xảy ra:</h3>
        <p>{str(e)}</p>
        <p>Thử đổi chế độ tải hoặc kiểm tra lại Link/Cookies.</p>
        <button onclick="window.history.back()">Quay lại</button>
        """, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
