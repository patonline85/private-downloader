import os
import glob
import time
from flask import Flask, render_template_string, request, send_file
from yt_dlp import YoutubeDL

app = Flask(__name__)

# --- CẤU HÌNH ---
# Sử dụng /tmp (thẻ nhớ) để an toàn. 
# Nếu muốn nhanh hơn có thể đổi thành '/dev/shm' (RAM) nhưng cẩn thận tràn RAM với video 4K.
TMP_DIR = '/tmp'

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Pháp Môn Tâm Linh 心靈法門</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, sans-serif; background: #f0f2f5; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .container { background: white; padding: 30px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); width: 90%; max-width: 450px; text-align: center; }
        
        .logo { max-width: 120px; height: auto; margin-bottom: 15px; border-radius: 12px; }
        h2 { text-align: center; color: #333; margin-bottom: 20px; margin-top: 0; }
        .input-group { margin-bottom: 15px; text-align: left; }
        label { display: block; margin-bottom: 5px; font-weight: 600; color: #555; font-size: 0.9em; }
        input[type="text"] { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; font-size: 16px; }
        select { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 8px; background: white; font-size: 16px; appearance: none; }
        button { background: #007aff; color: white; border: none; padding: 15px; border-radius: 8px; cursor: pointer; font-weight: bold; width: 100%; font-size: 16px; margin-top: 10px; transition: 0.2s; }
        button:hover { background: #005bb5; }
        .note { font-size: 12px; color: #888; margin-top: 20px; text-align: center; line-height: 1.5; }
        .warning { color: #d32f2f; font-size: 0.85em; margin-top: 5px; display: none; }
    </style>
    <script>
        function startLoading() {
            var btn = document.getElementById('dlBtn');
            var warn = document.getElementById('warnMsg');
            btn.innerText = '⏳ Server đang xử lý...';
            btn.style.backgroundColor = '#666';
            btn.disabled = true;
            warn.style.display = 'block';
            
            // Vì Flask không báo tiến độ, nên sau 3 giây reset nút để người dùng đỡ hoang mang
            // Nhưng thực tế Server vẫn đang chạy ngầm
            setTimeout(function() {
                btn.innerText = '⬇️ Đang tải về máy...';
                btn.style.backgroundColor = '#28a745'; // Màu xanh lá
            }, 5000);
        }
    </script>
</head>
<body>
    <div class="container">
        <img src="/static/logo.png" alt="App Logo" class="logo" onerror="this.style.display='none'">
        
        <h2>Pháp Môn Tâm Linh 心靈法門</h2>
        <form method="POST" action="/download" onsubmit="startLoading()">
            <div class="input-group">
                <label>Dán Link Video (Youtube/FB/TikTok):</label>
                <input type="text" name="url" placeholder="https://..." required>
            </div>
            <div class="input-group">
                <label>Chọn Chế Độ Tải:</label>
                <select name="mode">
                    <option value="original">⚡ Gốc (MKV 4K/8K) - Nét nhất</option>
                    <option value="mp4_convert">🍎 iPhone/Android (MP4 Full HD)</option>
                    <option value="audio_only">🎵 Chỉ lấy Audio (MP3)</option>
                </select>
            </div>
            <button type="submit" id="dlBtn">Tải Về Ngay</button>
            <p id="warnMsg" class="warning">⚠️ Video 4K cần thời gian ghép file. Vui lòng đợi khoảng 1-2 phút, trình duyệt sẽ tự tải xuống khi xong.</p>
        </form>
        <p class="note">Server: Armbian Home Lab</p>
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
    old_files = glob.glob(f'{TMP_DIR}/*')
    for f in old_files:
        try: os.remove(f)
        except: pass

    # Cấu hình chung cho yt-dlp
    ydl_opts = {
        'outtmpl': f'{TMP_DIR}/%(title).50s.%(ext)s', 
        'trim_file_name': 50,
        'restrictfilenames': True, # Tránh lỗi tên file tiếng Việt trên Linux
        'noplaylist': True,
        'cookiefile': 'cookies.txt',
        'ffmpeg_location': '/usr/bin/ffmpeg',
        'quiet': False, 
        'geo_bypass': True,
        # Giả lập trình duyệt để tránh bị chặn
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        }
    }

    # --- XỬ LÝ LOGIC ---
    if mode == 'mp4_convert':
        ydl_opts.update({
            # Tìm MP4 tốt nhất có sẵn để đỡ phải convert (nhanh hơn)
            'format': 'best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
            'merge_output_format': 'mp4',
            # Dùng preset ultrafast để ép FFmpeg chạy nhanh trên Armbian
            'postprocessor_args': ['-preset', 'ultrafast'],
        })
        
    elif mode == 'audio_only':
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
        
    else: # mode == 'original' (MKV 4K)
        ydl_opts.update({
            # --- FIX LỖI 4K Ở ĐÂY ---
            # Lấy Video xịn nhất + Audio xịn nhất (thường là WebM VP9 + Opus)
            'format': 'bestvideo+bestaudio/best',
            # Bắt buộc đóng gói vào MKV (để chứa được 4K và Audio xịn)
            'merge_output_format': 'mkv',
            # Tối ưu tốc độ ghép file cho chip ARM
            'postprocessor_args': ['-preset', 'ultrafast'],
        })

    try:
        # Thực thi tải
        with YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
            
        # Tìm file vừa tải
        list_of_files = glob.glob(f'{TMP_DIR}/*')
        
        # Lọc bỏ file rác và cookies
        valid_files = [f for f in list_of_files if not f.endswith('.txt') and not f.endswith('.part') and not f.endswith('.ytdl')]
        
        if not valid_files:
            return "❌ Lỗi: Không tìm thấy file. Link có thể sai hoặc Server bị chặn.", 500
            
        # Lấy file mới nhất
        latest_file = max(valid_files, key=os.path.getctime)
        
        # Tăng timeout cho quá trình gửi file (Flask send_file)
        return send_file(latest_file, as_attachment=True)

    except Exception as e:
        return f"""
        <div style="font-family: sans-serif; padding: 20px;">
            <h3>❌ Có lỗi xảy ra:</h3>
            <pre style="background: #eee; padding: 10px; border-radius: 5px;">{str(e)}</pre>
            <button onclick="window.history.back()" style="padding: 10px 20px; cursor: pointer;">Quay lại</button>
        </div>
        """, 500

if __name__ == '__main__':
    # Tắt debug để ổn định hơn
    app.run(host='0.0.0.0', port=5000, debug=False)
