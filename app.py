import os
import glob
import json
import time
import subprocess
import shutil
from flask import Flask, render_template_string, request, send_file, Response, stream_with_context, jsonify
from yt_dlp import YoutubeDL

app = Flask(__name__)

# --- CẤU HÌNH MÔI TRƯỜNG ---
# yt-dlp cần tìm thấy 'node' để giải mã n-challenge
def setup_environment():
    # 1. Thêm đường dẫn bin chuẩn
    os.environ['PATH'] = "/usr/bin:/usr/local/bin:/bin:" + os.environ.get('PATH', '')
    
    # 2. Xóa cache cũ của yt-dlp để tránh lưu lại các challenge thất bại
    try:
        shutil.rmtree('/root/.cache/yt-dlp', ignore_errors=True)
        shutil.rmtree('/.cache/yt-dlp', ignore_errors=True)
    except: pass

setup_environment()

# --- HTML TEMPLATE (Giữ nguyên hoặc dùng lại bản cũ của bạn) ---
# (Để tiết kiệm không gian, tôi dùng lại template cũ nhưng bạn nhớ giữ nguyên phần HTML trong code cũ của bạn)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Fixed YouTube Downloader</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: sans-serif; background: #121212; color: #fff; padding: 20px; }
        input { padding: 10px; width: 70%; }
        button { padding: 10px; cursor: pointer; }
        .log { background: #000; padding: 10px; font-family: monospace; margin-top: 10px; white-space: pre-wrap;}
    </style>
</head>
<body>
    <h2>YouTube Fixer 2.0 (Android Client)</h2>
    <div>
        <input type="text" id="url" placeholder="Link YouTube...">
        <button onclick="analyze()">Phân tích</button>
    </div>
    <div id="result" style="margin-top:20px"></div>
    <div id="logs" class="log" style="display:none"></div>

    <script>
        // (Giữ nguyên logic Javascript cũ của bạn hoặc copy lại từ file cũ)
        // Phần quan trọng là backend python bên dưới
        async function analyze() {
            const url = document.getElementById('url').value;
            const res = await fetch('/analyze', { method: 'POST', body: new URLSearchParams({url}) });
            const data = await res.json();
            if(data.error) alert(data.error);
            else {
                // Đơn giản hóa ví dụ để test
                document.getElementById('result').innerHTML = 
                    `<button onclick="download('${data.videos[0].id}', '${data.audios[0].id}')">Tải thử bản đầu tiên</button>`;
            }
        }
        async function download(vid, aud) {
            const url = document.getElementById('url').value;
            const formData = new FormData();
            formData.append('url', url);
            formData.append('video_id', vid);
            formData.append('audio_id', aud);
            const response = await fetch('/download_custom', { method: 'POST', body: formData });
            // ... Logic xử lý stream như cũ ...
        }
    </script>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def index():
    return render_template_string(HTML_TEMPLATE)

# --- HÀM CẤU HÌNH YT-DLP MỚI (FIX LỖI) ---
def get_ydl_opts():
    return {
        # 1. Bỏ cookie nếu đang bị lỗi 403/Challenge (Comment dòng dưới nếu muốn thử lại cookie)
        # 'cookiefile': 'cookies.txt', 
        
        'quiet': True,
        'no_warnings': True,
        'ffmpeg_location': '/usr/bin/ffmpeg',
        
        # 2. QUAN TRỌNG: Cấu hình Client sang Android để né SABR và n-challenge
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios'], # Giả lập App điện thoại
                'player_skip': ['web', 'tv'],        # Bỏ qua Web client đang bị lỗi
                'include_ssl_logs': [False]
            }
        },
        
        # 3. User Agent giả lập thiết bị thật
        'user_agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36',
        
        # 4. Tắt check certificate nếu gặp lỗi SSL trong Docker
        'nocheckcertificate': True,
    }

@app.route('/analyze', methods=['POST'])
def analyze():
    url = request.form.get('url')
    ydl_opts = get_ydl_opts()
    ydl_opts.update({'skip_download': True})

    try:
        with YoutubeDL(ydl_opts) as ydl:
            # Xóa cache mỗi lần chạy để đảm bảo lấy JS player mới nhất
            ydl.cache.remove()
            
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])

        video_opts = []
        audio_opts = []

        for f in formats:
            # Lọc Video
            if f.get('vcodec') != 'none' and f.get('acodec') == 'none':
                video_opts.append({
                    'id': f['format_id'],
                    'res': f.get('format_note') or f"{f.get('height')}p",
                    'ext': f['ext'],
                    'filesize': f.get('filesize') or 0
                })
            # Lọc Audio
            elif f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                audio_opts.append({
                    'id': f['format_id'],
                    'ext': f['ext'],
                    'abr': f.get('abr') or 0
                })
        
        # Sắp xếp
        video_opts.sort(key=lambda x: (x['filesize'] if x['filesize'] else 0), reverse=True)
        audio_opts.sort(key=lambda x: x['abr'], reverse=True)
        
        return jsonify({'videos': video_opts, 'audios': audio_opts})

    except Exception as e:
        print(f"LOI ANALYZE: {e}")
        return jsonify({'error': str(e)})

@app.route('/download_custom', methods=['POST'])
def download_custom():
    url = request.form.get('url')
    vid_id = request.form.get('video_id')
    aud_id = request.form.get('audio_id')

    def generate():
        # Clean tmp
        for f in glob.glob('/tmp/*'):
            try: os.remove(f)
            except: pass

        ydl_opts = get_ydl_opts()
        ydl_opts.update({
            'outtmpl': '/tmp/%(title)s.%(ext)s',
            'restrictfilenames': False, # Cho phép tên tiếng Việt
            'format': f"{vid_id}+{aud_id}",
            'merge_output_format': 'mp4',
        })

        try:
            yield json.dumps({'status': 'downloading'}) + "\n"
            with YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=True)
            yield json.dumps({'status': 'finished', 'filename': 'done'}) + "\n" # Đơn giản hóa response
        except Exception as e:
            yield json.dumps({'status': 'error', 'message': str(e)}) + "\n"

    return Response(stream_with_context(generate()), mimetype='text/plain')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
