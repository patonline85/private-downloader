import os
import glob
import uuid
import threading
import time
from flask import Flask, render_template_string, request, send_file, jsonify, url_for
from yt_dlp import YoutubeDL

app = Flask(__name__)

# --- CẤU HÌNH ---
TMP_DIR = '/tmp'
# Biến lưu trạng thái các tiến trình tải (Trong bộ nhớ RAM)
# Cấu trúc: {'task_id': {'status': 'processing/done/error', 'filename': '...', 'message': '...'}}
TASKS = {}

# --- GIAO DIỆN HTML (JAVASCRIPT NÂNG CẤP) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Pro Downloader V2</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #f2f2f7; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .container { background: white; padding: 25px; border-radius: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); width: 90%; max-width: 420px; text-align: center; }
        
        .logo { max-width: 100px; margin-bottom: 10px; border-radius: 18px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        h2 { margin: 10px 0 20px; color: #1c1c1e; font-size: 22px; }
        
        .input-group { margin-bottom: 15px; text-align: left; }
        label { font-size: 13px; font-weight: 600; color: #8e8e93; margin-bottom: 5px; display: block; text-transform: uppercase; letter-spacing: 0.5px; }
        input[type="text"], select { width: 100%; padding: 14px; border: 1px solid #e5e5ea; border-radius: 12px; font-size: 16px; background: #f9f9f9; box-sizing: border-box; outline: none; transition: 0.3s; }
        input:focus, select:focus { border-color: #007aff; background: #fff; }
        
        /* NÚT BẤM CHÍNH */
        .btn-main { background: #007aff; color: white; border: none; padding: 16px; border-radius: 14px; font-weight: bold; font-size: 17px; width: 100%; cursor: pointer; transition: 0.2s; display: block; }
        .btn-main:hover { background: #0062cc; transform: scale(0.98); }
        .btn-main:disabled { background: #aeaeb2; cursor: not-allowed; transform: none; }

        /* TRẠNG THÁI */
        #statusArea { display: none; margin-top: 20px; padding: 15px; background: #f2f2f7; border-radius: 12px; }
        .spinner { border: 4px solid rgba(0,0,0,0.1); width: 30px; height: 30px; border-radius: 50%; border-left-color: #007aff; animation: spin 1s linear infinite; margin: 0 auto 10px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .status-text { color: #3a3a3c; font-weight: 500; font-size: 15px; }

        /* NÚT LƯU FILE (HIỆN KHI XONG) */
        #resultArea { display: none; margin-top: 20px; animation: fadeIn 0.5s; }
        .btn-save { background: #34c759; color: white; text-decoration: none; padding: 16px; border-radius: 14px; font-weight: bold; font-size: 17px; display: block; width: 100%; box-sizing: border-box; box-shadow: 0 4px 15px rgba(52, 199, 89, 0.3); }
        .btn-save:hover { background: #2ebd4f; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

        .ios-note { font-size: 13px; color: #8e8e93; margin-top: 15px; line-height: 1.4; background: #fffbe6; padding: 10px; border-radius: 8px; border: 1px solid #fff5c2; display: none; }
    </style>
</head>
<body>
    <div class="container">
        <img src="/static/logo.png" alt="Logo" class="logo" onerror="this.style.display='none'">
        <h2>Server Downloader</h2>
        
        <div id="inputArea">
            <div class="input-group">
                <label>Liên kết Video</label>
                <input type="text" id="url" placeholder="Dán link vào đây..." required>
            </div>
            <div class="input-group">
                <label>Định dạng</label>
                <select id="mode">
                    <option value="original">⚡ Mặc định (Tự chọn tốt nhất)</option>
                    <option value="mp4_convert">📱 iPhone/Android (MP4 1080p)</option>
                    <option value="audio_only">🎧 Âm thanh (MP3)</option>
                </select>
            </div>
            <button class="btn-main" onclick="startTask()" id="startBtn">Bắt đầu tải</button>
        </div>

        <div id="statusArea">
            <div class="spinner"></div>
            <div class="status-text" id="statusMsg">Server đang xử lý...</div>
        </div>

        <div id="resultArea">
            <div style="margin-bottom: 10px; color: #34c759; font-weight: bold;">✅ Hoàn tất!</div>
            <a href="#" id="saveLink" class="btn-save" download>📥 LƯU VIDEO VỀ MÁY</a>
            
            <div class="ios-note" id="iosHint">
                <b>💡 Mẹo cho iPhone:</b><br>
                Bấm nút "Lưu Video", sau đó chọn "Lưu vào Tệp" (Save to Files) để giữ chất lượng gốc.
            </div>
            
            <button onclick="resetUI()" style="background:none; border:none; color:#007aff; margin-top:15px; cursor:pointer; font-size:14px;">Tải video khác</button>
        </div>
    </div>

    <script>
        // Kiểm tra xem có phải iPhone không để hiện hướng dẫn
        if (/iPad|iPhone|iPod/.test(navigator.userAgent)) {
            document.getElementById('iosHint').style.display = 'block';
        }

        async function startTask() {
            const url = document.getElementById('url').value;
            const mode = document.getElementById('mode').value;
            if (!url) return alert("Vui lòng nhập link!");

            // 1. Khóa giao diện
            document.getElementById('inputArea').style.opacity = '0.5';
            document.getElementById('startBtn').disabled = true;
            document.getElementById('statusArea').style.display = 'block';
            document.getElementById('resultArea').style.display = 'none';

            // 2. Gửi lệnh bắt đầu
            const formData = new FormData();
            formData.append('url', url);
            formData.append('mode', mode);

            try {
                const response = await fetch('/start_download', { method: 'POST', body: formData });
                const data = await response.json();
                
                if (data.task_id) {
                    pollStatus(data.task_id);
                } else {
                    throw new Error("Không lấy được Task ID");
                }
            } catch (err) {
                alert("Lỗi: " + err.message);
                resetUI();
            }
        }

        async function pollStatus(taskId) {
            const interval = setInterval(async () => {
                try {
                    const res = await fetch(`/check_status/${taskId}`);
                    const data = await res.json();

                    if (data.status === 'processing') {
                        // Vẫn đang chạy, không làm gì cả
                        document.getElementById('statusMsg').innerText = "Đang xử lý: " + data.message;
                    } else if (data.status === 'done') {
                        clearInterval(interval);
                        showResult(data.filename);
                    } else if (data.status === 'error') {
                        clearInterval(interval);
                        alert("Lỗi Server: " + data.message);
                        resetUI();
                    }
                } catch (e) {
                    clearInterval(interval);
                    alert("Mất kết nối với Server");
                    resetUI();
                }
            }, 1000); // Kiểm tra mỗi 1 giây
        }

        function showResult(filename) {
            document.getElementById('statusArea').style.display = 'none';
            document.getElementById('resultArea').style.display = 'block';
            
            // Cập nhật link tải
            const link = document.getElementById('saveLink');
            link.href = `/get_file/${filename}`;
        }

        function resetUI() {
            document.getElementById('inputArea').style.opacity = '1';
            document.getElementById('url').value = '';
            document.getElementById('startBtn').disabled = false;
            document.getElementById('statusArea').style.display = 'none';
            document.getElementById('resultArea').style.display = 'none';
        }
    </script>
</body>
</html>
"""

# --- HÀM XỬ LÝ NGẦM (BACKGROUND WORKER) ---
def download_worker(task_id, url, mode):
    try:
        TASKS[task_id] = {'status': 'processing', 'message': 'Đang tải xuống...'}
        
        # Dọn dẹp file cũ
        for f in glob.glob(f'{TMP_DIR}/*'):
            try:
                if os.path.getmtime(f) < time.time() - 1800: os.remove(f)
            except: pass

        # Cấu hình yt-dlp
        ydl_opts = {
            'outtmpl': f'{TMP_DIR}/%(title).50s_{task_id}.%(ext)s',
            'trim_file_name': 50,
            'restrictfilenames': True,
            'noplaylist': True,
            'cookiefile': 'cookies.txt',
            'ffmpeg_location': '/usr/bin/ffmpeg',
            'quiet': True,
            'http_headers': {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1'}
        }

        if mode == 'mp4_convert':
            TASKS[task_id]['message'] = 'Đang chuyển đổi sang MP4...'
            ydl_opts.update({
                'format': 'best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
                'merge_output_format': 'mp4',
                'postprocessor_args': ['-preset', 'ultrafast'],
            })
        elif mode == 'audio_only':
            TASKS[task_id]['message'] = 'Đang tách nhạc...'
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}],
            })
        else:
            TASKS[task_id]['message'] = 'Đang xử lý Video 4K...'
            ydl_opts.update({
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': 'mkv',
                'postprocessor_args': ['-preset', 'ultrafast'],
            })

        # Bắt đầu tải
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Tìm file kết quả
        search_pattern = f'{TMP_DIR}/*{task_id}*'
        found_files = glob.glob(search_pattern)
        valid_files = [f for f in found_files if not f.endswith('.part') and not f.endswith('.ytdl')]

        if valid_files:
            filename = os.path.basename(valid_files[0])
            TASKS[task_id] = {'status': 'done', 'filename': filename}
        else:
            TASKS[task_id] = {'status': 'error', 'message': 'Không tìm thấy file kết quả'}

    except Exception as e:
        TASKS[task_id] = {'status': 'error', 'message': str(e)}

# --- ROUTES ---
@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/start_download', methods=['POST'])
def start_download():
    task_id = uuid.uuid4().hex
    url = request.form.get('url')
    mode = request.form.get('mode')
    
    # Chạy thread riêng để không treo giao diện
    thread = threading.Thread(target=download_worker, args=(task_id, url, mode))
    thread.start()
    
    return jsonify({'task_id': task_id})

@app.route('/check_status/<task_id>')
def check_status(task_id):
    return jsonify(TASKS.get(task_id, {'status': 'error', 'message': 'Task not found'}))

@app.route('/get_file/<filename>')
def get_file(filename):
    # as_attachment=True là quan trọng để hiện hộp thoại Save thay vì Play
    return send_file(os.path.join(TMP_DIR, filename), as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
