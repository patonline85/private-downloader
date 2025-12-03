import os
import glob
import json
import time
from flask import Flask, render_template_string, request, send_file, Response, stream_with_context
from yt_dlp import YoutubeDL

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Server 4K Downloader</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, sans-serif; background: #121212; color: #e0e0e0; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .container { background: #1e1e1e; padding: 30px; border-radius: 12px; width: 90%; max-width: 500px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
        h2 { text-align: center; color: #fff; margin-bottom: 25px; }
        input, select { width: 100%; padding: 14px; margin-bottom: 15px; background: #2c2c2c; border: 1px solid #333; color: white; border-radius: 6px; box-sizing: border-box; font-size: 16px; }
        button { width: 100%; padding: 15px; background: #007aff; color: white; border: none; font-weight: bold; border-radius: 6px; cursor: pointer; font-size: 16px; transition: 0.2s; }
        button:hover { background: #0056b3; }
        button:disabled { background: #555; cursor: not-allowed; }
        
        .progress-container { margin-top: 20px; display: none; }
        .progress-bar-bg { width: 100%; background-color: #333; border-radius: 10px; overflow: hidden; height: 20px; }
        .progress-bar-fill { height: 100%; width: 0%; background-color: #28a745; transition: width 0.3s ease; }
        .status-text { text-align: center; margin-top: 10px; font-size: 0.9em; color: #aaa; font-family: monospace; }
        .download-link { display: none; margin-top: 15px; text-align: center; }
        .download-btn { background: #28a745; text-decoration: none; padding: 10px 20px; border-radius: 5px; color: white; font-weight: bold; display: inline-block; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🚀 High-Res Downloader</h2>
        <form id="dlForm">
            <input type="text" id="url" name="url" placeholder="Dán link Youtube/Facebook..." required>
            <select id="mode" name="mode">
                <option value="4k_mkv">🌟 4K/2K GỐC (MKV) - Nét nhất</option>
                <option value="safe_mp4">📱 iPhone (MP4 1080p) - Convert</option>
                <option value="mp3">🎵 MP3 (Audio Only)</option>
            </select>
            <button type="submit" id="submitBtn">Bắt đầu Tải</button>
        </form>

        <div class="progress-container" id="progressArea">
            <div class="progress-bar-bg">
                <div class="progress-bar-fill" id="progressBar"></div>
            </div>
            <div class="status-text" id="statusText">Đang kết nối Server...</div>
        </div>

        <div class="download-link" id="downloadArea">
            <p>✅ Đã xử lý xong!</p>
            <a href="#" id="finalLink" class="download-btn">Lưu File Về Máy</a>
        </div>
    </div>

    <script>
        document.getElementById('dlForm').onsubmit = async function(e) {
            e.preventDefault();
            const btn = document.getElementById('submitBtn');
            const progressArea = document.getElementById('progressArea');
            const progressBar = document.getElementById('progressBar');
            const statusText = document.getElementById('statusText');
            const downloadArea = document.getElementById('downloadArea');
            
            btn.disabled = true;
            downloadArea.style.display = 'none';
            progressArea.style.display = 'block';
            progressBar.style.width = '0%';
            statusText.innerText = 'Đang khởi động...';
            
            const formData = new FormData();
            formData.append('url', document.getElementById('url').value);
            formData.append('mode', document.getElementById('mode').value);

            try {
                const response = await fetch('/stream_download', { method: 'POST', body: formData });
                const reader = response.body.getReader();
                const decoder = new TextDecoder();

                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;
                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\\n');
                    for (const line of lines) {
                        if (!line.trim()) continue;
                        try {
                            const data = JSON.parse(line);
                            if (data.status === 'downloading') {
                                progressBar.style.width = data.percent + '%';
                                statusText.innerText = `Đang tải: ${data.percent}% | Tốc độ: ${data.speed || '...'}`;
                            } else if (data.status === 'merging') {
                                progressBar.style.width = '99%';
                                progressBar.style.backgroundColor = '#ffc107'; 
                                statusText.innerText = 'Đang ghép file (Merge)... Vui lòng đợi!';
                            } else if (data.status === 'finished') {
                                progressBar.style.width = '100%';
                                statusText.innerText = 'Hoàn tất!';
                                document.getElementById('finalLink').href = '/get_file/' + encodeURIComponent(data.filename);
                                downloadArea.style.display = 'block';
                                btn.disabled = false;
                            } else if (data.status === 'error') {
                                statusText.innerText = 'Lỗi: ' + data.message;
                                statusText.style.color = 'red';
                                btn.disabled = false;
                            }
                        } catch (err) {}
                    }
                }
            } catch (error) {
                statusText.innerText = 'Lỗi kết nối Server!';
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

@app.route('/stream_download', methods=['POST'])
def stream_download():
    url = request.form.get('url')
    mode = request.form.get('mode')

    def generate():
        for f in glob.glob('/tmp/*'):
            try: os.remove(f)
            except: pass

        def progress_hook(d):
            if d['status'] == 'downloading':
                p = d.get('_percent_str', '0%').replace('%','')
                s = d.get('_speed_str', 'N/A')
                yield json.dumps({'status': 'downloading', 'percent': p, 'speed': s}) + "\n"
            elif d['status'] == 'finished':
                yield json.dumps({'status': 'merging'}) + "\n"

        ydl_opts = {
            'outtmpl': '/tmp/%(title)s.%(ext)s',
            'restrictfilenames': True,
            'noplaylist': True,
            'cookiefile': 'cookies.txt',
            'ffmpeg_location': '/usr/bin/ffmpeg',
            'quiet': True,
            'progress_hooks': [progress_hook],
            
            # --- CHIẾN THUẬT CLIENT MỚI: ANDROID CREATOR ---
            # Đây là client dành cho Youtube Studio, thường bypass tốt hơn
            # Và fallback về 'web' nếu cần (lúc này đã có NodeJS nên web sẽ chạy ngon)
            'extractor_args': {
                'youtube': {
                    'player_client': ['android_creator', 'web'], 
                    'player_skip': ['webpage', 'configs', 'js'], 
                }
            },
        }

        if mode == '4k_mkv':
            ydl_opts.update({'format': 'bestvideo+bestaudio', 'merge_output_format': 'mkv'})
        elif mode == 'safe_mp4':
            ydl_opts.update({'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best', 'merge_output_format': 'mp4'})
        elif mode == 'mp3':
            ydl_opts.update({'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}]})

        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=True)
            
            files = [f for f in glob.glob('/tmp/*') if not f.endswith('.txt') and not f.endswith('.part')]
            if files:
                final_file = max(files, key=os.path.getctime)
                yield json.dumps({'status': 'finished', 'filename': os.path.basename(final_file)}) + "\n"
            else:
                yield json.dumps({'status': 'error', 'message': 'Không tìm thấy file sau khi tải'}) + "\n"

        except Exception as e:
            yield json.dumps({'status': 'error', 'message': str(e)}) + "\n"

    return Response(stream_with_context(generate()), mimetype='text/plain')

@app.route('/get_file/<filename>')
def get_file(filename):
    safe_path = os.path.join('/tmp', filename)
    if os.path.exists(safe_path):
        return send_file(safe_path, as_attachment=True)
    else:
        return "File not found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
