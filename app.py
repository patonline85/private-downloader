import os
import glob
import json
import time
from flask import Flask, render_template_string, request, send_file, Response, stream_with_context
from yt_dlp import YoutubeDL

app = Flask(__name__)

# --- GIAO DIỆN HTML + CSS + JS (Đã nâng cấp) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Pro Downloader @Armbian</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, sans-serif; background: #f0f2f5; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .container { background: white; padding: 25px; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); width: 90%; max-width: 450px; }
        h2 { text-align: center; color: #333; margin-bottom: 20px; }
        
        /* 1. CSS CHO Ô NHẬP LIỆU KÈM NÚT DÁN/XÓA */
        .input-group { position: relative; margin-bottom: 15px; display: flex; align-items: center; }
        .input-wrapper { position: relative; width: 100%; }
        input[type="text"] { width: 100%; padding: 12px 85px 12px 12px; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; font-size: 16px; }
        
        /* Các nút icon nằm trong ô input */
        .action-btns { position: absolute; right: 5px; top: 50%; transform: translateY(-50%); display: flex; gap: 5px; }
        .icon-btn { background: #eee; border: none; padding: 5px 10px; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600; color: #555; transition: 0.2s; }
        .icon-btn:hover { background: #ddd; }

        select { width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 8px; background: white; font-size: 16px; margin-bottom: 15px; }
        
        /* Nút Tải chính */
        button#submitBtn { background: #007aff; color: white; border: none; padding: 15px; border-radius: 8px; cursor: pointer; font-weight: bold; width: 100%; font-size: 16px; margin-top: 10px; transition: 0.2s; }
        button#submitBtn:hover { background: #005bb5; }
        button#submitBtn:disabled { background: #ccc; cursor: not-allowed; }

        /* 3. CSS CHO THANH TIẾN TRÌNH */
        .progress-container { margin-top: 20px; display: none; }
        .progress-bg { width: 100%; background-color: #eee; border-radius: 10px; height: 14px; overflow: hidden; }
        .progress-bar { height: 100%; width: 0%; background-color: #34c759; transition: width 0.3s ease; }
        .status-text { text-align: center; font-size: 0.9em; color: #666; margin-top: 5px; font-family: monospace; }

        /* Khu vực tải file xong */
        #downloadArea { display: none; margin-top: 20px; text-align: center; }
        .save-btn { display: inline-block; padding: 12px 30px; background: #34c759; color: white; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px; }
        
        .error-msg { color: #ff3b30; text-align: center; margin-top: 15px; display: none; word-break: break-word; font-size: 0.9em; background: #fff0f0; padding: 10px; border-radius: 8px;}
        .note { font-size: 12px; color: #888; margin-top: 20px; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🚀 Server Downloader</h2>
        
        <div class="input-group">
            <div class="input-wrapper">
                <input type="text" id="url" placeholder="Dán link (Youtube/FB/TikTok)..." required>
                <div class="action-btns">
                    <button type="button" class="icon-btn" onclick="pasteLink()" title="Dán từ Clipboard">📋 Dán</button>
                    <button type="button" class="icon-btn" onclick="clearLink()" title="Xóa trắng">✕</button>
                </div>
            </div>
        </div>

        <select id="mode">
            <option value="original">⚡ Gốc (Tốt nhất + Tên chuẩn)</option>
            <option value="mp4_convert">🍎 iPhone Chuẩn (MP4 1080p)</option>
            <option value="audio_only">🎵 Chỉ lấy Audio (MP3)</option>
        </select>

        <button id="submitBtn" onclick="startDownload()">Tải Về Ngay</button>

        <div class="progress-container" id="progressArea">
            <div class="progress-bg">
                <div class="progress-bar" id="progressBar"></div>
            </div>
            <div class="status-text" id="statusText">Đang kết nối...</div>
        </div>

        <div id="downloadArea">
            <p>✅ Đã xử lý xong!</p>
            <a href="#" id="finalLink" class="save-btn" onclick="resetUI()">💾 Lưu Video Về Máy</a>
        </div>
        
        <p id="errorText" class="error-msg"></p>
        <p class="note">Server: Armbian Home Lab</p>
    </div>

    <script>
        // 1. CHỨC NĂNG DÁN LINK
        async function pasteLink() {
            try {
                const text = await navigator.clipboard.readText();
                document.getElementById('url').value = text;
            } catch (err) { alert('Trình duyệt không cho phép dán tự động. Hãy dán thủ công.'); }
        }

        // 1. CHỨC NĂNG XÓA LINK
        function clearLink() {
            document.getElementById('url').value = '';
            document.getElementById('url').focus();
            // Ẩn các thông báo cũ nếu có
            document.getElementById('progressArea').style.display = 'none';
            document.getElementById('downloadArea').style.display = 'none';
            document.getElementById('errorText').style.display = 'none';
            document.getElementById('submitBtn').disabled = false;
            document.getElementById('submitBtn').innerText = "Tải Về Ngay";
        }

        // 2. CHỨC NĂNG RESET UI (Sau khi bấm lưu file)
        function resetUI() {
            setTimeout(() => {
                document.getElementById('submitBtn').disabled = false;
                document.getElementById('submitBtn').innerText = "Tải Về Ngay";
                document.getElementById('progressArea').style.display = 'none';
                document.getElementById('downloadArea').style.display = 'none';
                document.getElementById('errorText').style.display = 'none';
                document.getElementById('progressBar').style.width = '0%';
            }, 2000); // Reset sau 2 giây
        }

        // 3. LOGIC TẢI VÀ TIẾN TRÌNH (STREAMING)
        async function startDownload() {
            const url = document.getElementById('url').value;
            const mode = document.getElementById('mode').value;
            
            if (!url) return alert("Vui lòng nhập link!");

            // Cập nhật giao diện: Khóa nút, hiện loading
            const btn = document.getElementById('submitBtn');
            const progressArea = document.getElementById('progressArea');
            const progressBar = document.getElementById('progressBar');
            const statusText = document.getElementById('statusText');
            const downloadArea = document.getElementById('downloadArea');
            const errorText = document.getElementById('errorText');

            btn.disabled = true;
            btn.innerText = "⏳ Đang xử lý... (Đừng tắt)";
            downloadArea.style.display = 'none';
            errorText.style.display = 'none';
            progressArea.style.display = 'block';
            progressBar.style.width = '0%';
            statusText.innerText = 'Đang khởi động Server...';

            const formData = new FormData();
            formData.append('url', url);
            formData.append('mode', mode);

            try {
                // Gọi API Streaming thay vì API thường
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
                                // Cập nhật thanh tiến trình
                                progressBar.style.width = data.percent + '%';
                                statusText.innerText = `Đang tải: ${data.percent}% | ${data.speed}`;
                            } else if (data.status === 'merging') {
                                progressBar.style.width = '95%';
                                progressBar.style.backgroundColor = '#ffcc00';
                                statusText.innerText = 'Đang ghép file (Merge)...';
                            } else if (data.status === 'finished') {
                                // Hoàn tất
                                progressBar.style.width = '100%';
                                progressBar.style.backgroundColor = '#34c759';
                                statusText.innerText = 'Hoàn tất!';
                                
                                // Hiện nút lưu file
                                document.getElementById('finalLink').href = '/get_file/' + encodeURIComponent(data.filename);
                                downloadArea.style.display = 'block';
                                
                                // Reset nút tải để sẵn sàng cho bài mới
                                btn.disabled = false;
                                btn.innerText = "Tải File Khác";
                            } else if (data.status === 'error') {
                                throw new Error(data.message);
                            }
                        } catch (err) {
                            if (err.message && !err.message.includes("JSON")) {
                                errorText.innerText = "Lỗi: " + err.message;
                                errorText.style.display = 'block';
                                progressArea.style.display = 'none';
                                btn.disabled = false;
                                btn.innerText = "Thử Lại";
                            }
                        }
                    }
                }
            } catch (error) {
                errorText.innerText = "Lỗi kết nối Server: " + error;
                errorText.style.display = 'block';
                btn.disabled = false;
                btn.innerText = "Thử Lại";
            }
        }
    </script>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def index():
    return render_template_string(HTML_TEMPLATE)

# --- BACKEND XỬ LÝ STREAMING ---
@app.route('/stream_download', methods=['POST'])
def stream_download():
    url = request.form.get('url')
    mode = request.form.get('mode')

    def generate():
        # Dọn dẹp file cũ
        for f in glob.glob('/tmp/*'):
            try: os.remove(f)
            except: pass

        # Hook để bắt tiến độ tải từ yt-dlp
        def progress_hook(d):
            if d['status'] == 'downloading':
                # Lấy % và tốc độ
                p = d.get('_percent_str', '0%').replace('%','').strip()
                s = d.get('_speed_str', 'N/A')
                # Gửi về client để vẽ thanh loading
                yield json.dumps({'status': 'downloading', 'percent': p, 'speed': s}) + "\n"
            elif d['status'] == 'finished':
                yield json.dumps({'status': 'merging'}) + "\n"

        # Cấu hình yt-dlp (Giữ nguyên logic ổn định cũ)
        ydl_opts = {
            'outtmpl': '/tmp/%(title)s.%(ext)s', # Lấy tên gốc
            'trim_file_name': 200,
            'restrictfilenames': False,          # Cho phép tiếng Việt
            'noplaylist': True,
            'cookiefile': 'cookies.txt',
            'ffmpeg_location': '/usr/bin/ffmpeg',
            'cachedir': False,
            'quiet': True,
            'progress_hooks': [progress_hook],   # Gắn hook vào đây
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
            'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        }

        # Logic chọn định dạng
        if mode == 'mp4_convert':
            ydl_opts.update({
                'format': 'bv*+ba/b[ext=mp4]/b',
                'merge_output_format': 'mp4',
                'postprocessors': [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}],
            })
        elif mode == 'audio_only':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
            })
        else: # original
            ydl_opts.update({
                'format': 'bv*+ba/b',
            })

        try:
            # Bắt đầu tải
            with YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=True)
            
            # Tìm file kết quả
            files = [f for f in glob.glob('/tmp/*') if not f.endswith('.txt') and not f.endswith('.part')]
            
            if files:
                # Lấy file mới nhất
                final_file = max(files, key=os.path.getctime)
                filename = os.path.basename(final_file)
                # Báo thành công và trả về tên file
                yield json.dumps({'status': 'finished', 'filename': filename}) + "\n"
            else:
                yield json.dumps({'status': 'error', 'message': 'Không tìm thấy file tải về.'}) + "\n"

        except Exception as e:
            yield json.dumps({'status': 'error', 'message': str(e)}) + "\n"

    # Trả về Stream
    return Response(stream_with_context(generate()), mimetype='text/plain')

# API Tải file về máy
@app.route('/get_file/<filename>')
def get_file(filename):
    safe_path = os.path.join('/tmp', filename)
    if os.path.exists(safe_path):
        return send_file(safe_path, as_attachment=True)
    return "Not Found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
