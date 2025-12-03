import os
import glob
from flask import Flask, render_template_string, request, send_file
from yt_dlp import YoutubeDL

app = Flask(__name__)

# Giao diện HTML (Giữ nguyên như bản ổn định bạn gửi)
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
                    <option value="original">⚡ Gốc (Auto Best) - An toàn nhất</option>
                    <option value="mp4_convert">🍎 iPhone Chuẩn (MP4) - Ép Convert</option>
                    <option value="audio_only">🎵 Chỉ lấy Audio (MP3)</option>
                </select>
            </div>
            <button type="submit" onclick="this.innerText='⏳ Đang xử lý... (Đừng tắt)'">Tải Về Ngay</button>
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
    
    # 1. Dọn dẹp sạch sẽ thư mục tmp TRƯỚC khi tải
    # (Để đảm bảo file tìm thấy sau này chính là file vừa tải)
    old_files = glob.glob('/tmp/*')
    for f in old_files:
        try: os.remove(f)
        except: pass

    # Cấu hình cơ bản
    ydl_opts = {
        # --- CẬP NHẬT QUAN TRỌNG: SỬA TÊN FILE ---
        # Dùng %(title)s để lấy tên gốc của video
        # restrictfilenames=True sẽ tự động bỏ dấu tiếng Việt và ký tự lạ để tránh lỗi file
        'outtmpl': '/tmp/%(title)s.%(ext)s', 
        'restrictfilenames': True,
        # -----------------------------------------
        
        'noplaylist': True,
        'cookiefile': 'cookies.txt',
        'ffmpeg_location': '/usr/bin/ffmpeg',
        'cachedir': False,
        'quiet': False, # Bật log để debug
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'], # Quay về android thường cho ổn định
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
    }

    # --- XỬ LÝ LOGIC "MỀM MỎNG" HƠN ---
    
    if mode == 'mp4_convert':
        ydl_opts.update({
            # Dùng bv* thay vì bestvideo để không bắt buộc phải có video rời
            'format': 'bv*+ba/b[ext=mp4]/b', 
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
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
        
    else: # mode == 'original' (An toàn nhất)
        ydl_opts.update({
            # CÔNG THỨC THẦN THÁNH FIX LỖI:
            # bv*+ba: Lấy video rời + audio rời (nếu có)
            # /b: Nếu không có, lấy file gộp tốt nhất (best)
            # Không ép merge_output_format để tránh lỗi format not available
            'format': 'bv*+ba/b', 
        })

    try:
        # Thực thi tải
        with YoutubeDL(ydl_opts) as ydl:
            ydl.extract_info(url, download=True)
            
        # --- LOGIC TÌM FILE THÔNG MINH ---
        # Thay vì đoán tên, ta quét xem file nào vừa xuất hiện trong /tmp
        # Loại trừ cookies.txt nếu lỡ copy vào đó
        list_of_files = glob.glob('/tmp/*')
        if not list_of_files:
            return "❌ Lỗi: Không tìm thấy file tải về (Có thể bị Youtube chặn hoặc lỗi mạng)", 500
            
        # Tìm file mới nhất (vừa tải xong)
        latest_file = max(list_of_files, key=os.path.getctime)
        
        # Nếu lỡ bắt nhầm file cookies hoặc file rác hệ thống
        if "cookies.txt" in latest_file:
             # Tìm file lớn thứ nhì hoặc lọc theo đuôi
             files_video = [f for f in list_of_files if not f.endswith('.txt')]
             if files_video:
                 latest_file = max(files_video, key=os.path.getctime)
             else:
                 return "❌ Lỗi: Chỉ thấy file cookies, không thấy video.", 500

        # Gửi file về với tên gốc đã được yt-dlp đặt
        # Flask sẽ tự động lấy tên file từ đường dẫn latest_file
        return send_file(latest_file, as_attachment=True)

    except Exception as e:
        return f"""
        <div style="font-family: sans-serif; padding: 20px;">
            <h3>❌ Có lỗi xảy ra:</h3>
            <pre style="background: #eee; padding: 10px; border-radius: 5px;">{str(e)}</pre>
            <p><b>Cách khắc phục:</b></p>
            <ul>
                <li>Thử chọn chế độ "Gốc (Auto Best)"</li>
                <li>Link video có thể là Livestream hoặc Private</li>
                <li>Cookies có thể đã hết hạn -> Cần update cookies.txt mới</li>
            </ul>
            <button onclick="window.history.back()" style="padding: 10px 20px; cursor: pointer;">Quay lại</button>
        </div>
        """, 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
