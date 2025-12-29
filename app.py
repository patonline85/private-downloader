import os
import glob
import json
import time
import uuid  # <--- ĐÃ THÊM IMPORT UUID
from flask import Flask, render_template_string, request, send_file, Response, stream_with_context
from yt_dlp import YoutubeDL

app = Flask(__name__)

# --- GIAO DIỆN KHÔNG ĐỔI (Đã ẩn bớt để gọn code) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Pháp Môn Tâm Linh 心靈法門</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root { --bg-color: #f4f1ea; --card-bg: #ffffff; --primary-color: #8d6e63; --accent-color: #5d4037; --text-color: #4e342e; --success-color: #689f38; --border-radius: 12px; }
        body { font-family: 'Segoe UI', sans-serif; background: var(--bg-color); display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; color: var(--text-color); }
        .container { background: var(--card-bg); padding: 30px; border-radius: var(--border-radius); box-shadow: 0 8px 30px rgba(93, 64, 55, 0.15); width: 90%; max-width: 480px; border-top: 5px solid var(--accent-color); }
        h2 { text-align: center; color: var(--accent-color); margin-bottom: 25px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
        .input-group { position: relative; margin-bottom: 20px; }
        input[type="text"] { width: 100%; padding: 14px 90px 14px 15px; border: 2px solid #e0e0e0; border-radius: var(--border-radius); box-sizing: border-box; font-size: 16px; outline: none; transition: 0.3s; background: #fafafa; }
        input[type="text"]:focus { border-color: var(--primary-color); background: #fff; }
        .action-btns { position: absolute; right: 8px; top: 50%; transform: translateY(-50%); display: flex; gap: 5px; }
        .icon-btn { background: #efebe9; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; color: var(--accent-color); font-weight: bold; }
        .icon-btn:hover { background: #d7ccc8; }
        select { width: 100%; padding: 14px; border: 2px solid #e0e0e0; border-radius: var(--border-radius); background: #fff; font-size: 16px; margin-bottom: 20px; color: var(--text-color); }
        button#submitBtn { background: var(--accent-color); color: white; border: none; padding: 16px; border-radius: var(--border-radius); cursor: pointer; font-weight: bold; width: 100%; font-size: 16px; transition: 0.3s; box-shadow: 0 4px 10px rgba(93, 64, 55, 0.3); }
        button#submitBtn:hover { background: #3e2723; transform: translateY(-1px); }
        button#submitBtn:disabled { background: #bdbdbd; cursor: not-allowed; transform: none; box-shadow: none; }
        .progress-container { margin-top: 25px; display: none; }
        .progress-bg { width: 100%; background-color: #efebe9; border-radius: 20px; height: 10px; overflow: hidden; }
        .progress-bar { height: 100%; width: 0%; background-color: var(--success-color); transition: width 0.3s ease; }
        .status-text { text-align: center; font-size: 0.9em; color: var(--primary-color); margin-top: 8px; font-style: italic; }
        #downloadArea { display: none; margin-top: 25px; text-align: center; border-top: 1px dashed #d7ccc8; padding-top: 20px; }
        .save-btn { display: inline-block; padding: 14px 35px; background: var(--success-color); color: white; text-decoration: none; border-radius: var(--border-radius); font-weight: bold; font-size: 16px; box-shadow: 0 4px 10px rgba(104, 159, 56, 0.3); }
        .save-btn:hover { background: #558b2f; }
        .error-msg { color: #c62828; text-align: center; margin-top: 15px; display: none; background: #ffebee; padding: 12px; border-radius: 8px; font-size: 0.9em; }
        .note { font-size: 12px; color: #a1887f; margin-top: 25px; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Pháp Môn Tâm Linh 心靈法門</h2>
        <div class="input-group">
            <input type="text" id="url" placeholder="Dán liên kết vào đây..." required>
            <div class="action-btns">
                <button type="button" class="icon-btn" onclick="pasteLink()">Dán</button>
                <button type="button" class="icon-btn" onclick="clearLink()">Xóa</button>
            </div>
        </div>
        <select id="mode">
            <option value="original">🌟 Nguyên Bản (MKV 4K/8K - Rõ Nhất)</option>
            <option value="mp4_convert">📱 iPhone/Android (MP4 1080p)</option>
            <option value="audio_only">🎧 Chỉ Lấy Âm Thanh (MP3)</option>
        </select>
        <button id="submitBtn" onclick="startDownload()">Bắt Đầu Tải Về</button>
        <div class="progress-container" id="progressArea">
            <div class="progress-bg"><div class="progress-bar" id="progressBar"></div></div>
            <div class="status-text" id="statusText">Đang kết nối...</div>
        </div>
        <div id="downloadArea">
            <p style="color: var(--success-color); font-weight: bold;">✅ Đã hoàn tất!</p>
            <a href="#" id="finalLink" class="save-btn" onclick="resetUI()">Lưu Về Máy</a>
        </div>
        <p id="errorText" class="error-msg"></p>
        <p class="note">PMTL.SITE • BÌNH AN & TIỆN LỢI</p>
    </div>
    <script>
        async function pasteLink() { try { document.getElementById('url').value = await navigator.clipboard.readText(); } catch (err) { alert('Vui lòng dán thủ công'); } }
        function clearLink() {
            document.getElementById('url').value = '';
            document.getElementById('progressArea').style.display = 'none';
            document.getElementById('downloadArea').style.display = 'none';
            document.getElementById('errorText').style.display = 'none';
            document.getElementById('submitBtn').disabled = false;
        }
        function resetUI() { setTimeout(() => { clearLink(); }, 3000); }
        async function startDownload() {
            const url = document.getElementById('url').value;
            const mode = document.getElementById('mode').value;
            if (!url) return alert("Bạn chưa nhập liên kết!");
            const btn = document.getElementById('submitBtn');
            const progressArea = document.getElementById('progressArea');
            const progressBar = document.getElementById('progressBar');
            const statusText = document.getElementById('statusText');
            const downloadArea = document.getElementById('downloadArea');
            const errorText = document.getElementById('errorText');
            btn.disabled = true; btn.innerText = "⏳ Đang xử lý...";
            downloadArea.style.display = 'none'; errorText.style.display = 'none';
            progressArea.style.display = 'block'; progressBar.style.width = '5%'; statusText.innerText = 'Đang khởi động...';
            const formData = new FormData(); formData.append('url', url); formData.append('mode', mode);
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
                                statusText.innerText = `Đang tải: ${data.percent}% (${data.speed})`;
                            } else if (data.status === 'merging') {
                                progressBar.style.width = '98%';
                                statusText.innerText = 'Đang ghép file... (Vui lòng đợi)';
                            } else if (data.status === 'finished') {
                                progressBar.style.width = '100%';
                                statusText.innerText = 'Thành công!';
                                document.getElementById('finalLink').href = '/get_file/' + encodeURIComponent(data.filename);
                                downloadArea.style.display = 'block';
                                btn.innerText = "Tải File Khác"; btn.disabled = false;
                            } else if (data.status === 'error') { throw new Error(data.message); }
                        } catch (err) { if (err.message && !err.message.includes("JSON")) throw err; }
                    }
                }
            } catch (error) {
                errorText.innerText = "Lỗi: " + error.message; errorText.style.display = 'block';
                btn.disabled = false; btn.innerText = "Thử Lại"; progressArea.style.display = 'none';
            }
        }
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
        # --- DỌN DẸP FILE RÁC AN TOÀN ---
        current_time = time.time()
        retention_period = 1800  # 30 phút
        
        # Quét dọn các file cũ
        for f in glob.glob('/tmp/*'):
            try:
                # Chỉ xử lý file (không xử lý thư mục con nếu có)
                if not os.path.isfile(f): continue
                
                # Lấy thời gian sửa đổi cuối cùng
                file_mtime = os.path.getmtime(f)
                
                # Xóa nếu cũ hơn 30 phút
                if (current_time - file_mtime) > retention_period:
                    os.remove(f)
            except Exception as e:
                print(f"Không thể xóa file rác {f}: {e}")

        def progress_hook(d):
            if d['status'] == 'downloading':
                p = d.get('_percent_str', '0%').replace('%','').strip()
                s = d.get('_speed_str', 'N/A')
                yield json.dumps({'status': 'downloading', 'percent': p, 'speed': s}) + "\n"
            elif d['status'] == 'finished':
                yield json.dumps({'status': 'merging'}) + "\n"
                
        # Tạo ID riêng cho lần tải này
        unique_id = str(uuid.uuid4())[:8]
        
        ydl_opts = {
            # Gắn ID vào tên file để tìm lại chính xác
            'outtmpl': f'/tmp/%(title).50s_{unique_id}.%(ext)s',
            'trim_file_name': 50,
            'restrictfilenames': True,
            'noplaylist': True,
            'ffmpeg_location': '/usr/bin/ffmpeg',
            'quiet': True,
            'progress_hooks': [progress_hook],
            'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        }

        # --- LOGIC CHỌN ĐỊNH DẠNG ---
        if mode == 'mp4_convert':
             ydl_opts.update({
                'format': 'bv*[vcodec^=avc]+ba[ext=m4a]/b[ext=mp4]/b',
                'merge_output_format': 'mp4'
            })
        elif mode == 'audio_only':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
            })
        else: 
            ydl_opts.update({
                'format': 'bv*+ba/b', 
                'merge_output_format': 'mkv'
            })

        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # --- LOGIC TÌM FILE CHÍNH XÁC ---
            # Thay vì tìm file mới nhất, ta tìm file CÓ CHỨA unique_id
            search_pattern = f'/tmp/*{unique_id}*'
            found_files = glob.glob(search_pattern)
            
            # Lọc bỏ các file tạm (.part, .ytdl) nếu còn sót
            valid_files = [f for f in found_files if not f.endswith('.part') and not f.endswith('.ytdl')]
            
            if valid_files:
                # Lấy file đầu tiên tìm thấy (thường chỉ có 1)
                final_file_path = valid_files[0]
                filename = os.path.basename(final_file_path)
                yield json.dumps({'status': 'finished', 'filename': filename}) + "\n"
            else:
                yield json.dumps({'status': 'error', 'message': 'Lỗi: Không tìm thấy file sau khi tải.'}) + "\n"

        except Exception as e:
            error_msg = str(e)
            if "Requested format is not available" in error_msg:
                error_msg = "Video này chặn tải chất lượng cao. Vui lòng thử lại sau."
            yield json.dumps({'status': 'error', 'message': error_msg}) + "\n"

    return Response(stream_with_context(generate()), mimetype='text/plain')

@app.route('/get_file/<filename>')
def get_file(filename):
    # Chỉ cho phép tên file nằm trong /tmp và không chứa đường dẫn lùi ".."
    safe_path = os.path.join('/tmp', filename)
    
    # Kiểm tra bảo mật cơ bản
    if os.path.isfile(safe_path) and safe_path.startswith('/tmp/'):
        return send_file(safe_path, as_attachment=True)
    return "File Not Found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
