import os
import glob
import uuid
import threading
import time
import json
import shutil
from flask import Flask, render_template_string, request, send_file, jsonify
from yt_dlp import YoutubeDL

app = Flask(__name__)

# --- CẤU HÌNH ---
TMP_DIR = '/tmp'
STATUS_DIR = '/tmp/status'
os.makedirs(STATUS_DIR, exist_ok=True)
os.makedirs(TMP_DIR, exist_ok=True)

def save_status(task_id, data):
    with open(f'{STATUS_DIR}/{task_id}.json', 'w') as f:
        json.dump(data, f)

def load_status(task_id):
    path = f'{STATUS_DIR}/{task_id}.json'
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return None

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Pro Downloader V4 (Final)</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, sans-serif; background: #f2f2f7; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }
        .container { background: white; padding: 25px; border-radius: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); width: 90%; max-width: 420px; text-align: center; }
        .logo { max-width: 100px; margin-bottom: 10px; border-radius: 18px; }
        h2 { margin: 10px 0 20px; color: #1c1c1e; font-size: 22px; }
        .input-group { margin-bottom: 15px; text-align: left; }
        label { font-size: 13px; font-weight: 600; color: #8e8e93; display: block; margin-bottom: 5px; text-transform: uppercase; }
        input[type="text"], select { width: 100%; padding: 14px; border: 1px solid #e5e5ea; border-radius: 12px; font-size: 16px; background: #f9f9f9; box-sizing: border-box; }
        .btn-main { background: #007aff; color: white; border: none; padding: 16px; border-radius: 14px; font-weight: bold; font-size: 17px; width: 100%; cursor: pointer; display: block; }
        .btn-main:disabled { background: #aeaeb2; cursor: not-allowed; }
        #statusArea { display: none; margin-top: 20px; padding: 15px; background: #f2f2f7; border-radius: 12px; }
        .spinner { border: 4px solid rgba(0,0,0,0.1); width: 30px; height: 30px; border-radius: 50%; border-left-color: #007aff; animation: spin 1s linear infinite; margin: 0 auto 10px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        #resultArea { display: none; margin-top: 20px; }
        .btn-save { background: #34c759; color: white; text-decoration: none; padding: 16px; border-radius: 14px; font-weight: bold; font-size: 17px; display: block; width: 100%; box-sizing: border-box; }
        .ios-note { font-size: 13px; color: #8e8e93; margin-top: 15px; background: #fffbe6; padding: 10px; border-radius: 8px; border: 1px solid #fff5c2; display: none; }
    </style>
</head>
<body>
    <div class="container">
        <img src="/static/logo.png" alt="Logo" class="logo" onerror="this.style.display='none'">
        <h2>Server Downloader V4</h2>
        
        <div id="inputArea">
            <div class="input-group">
                <label>Liên kết Video</label>
                <input type="text" id="url" placeholder="Dán link vào đây..." required>
            </div>
            <div class="input-group">
                <label>Định dạng</label>
                <select id="mode">
                    <option value="original">⚡ Gốc (4K/8K MKV)</option>
                    <option value="mp4_convert">📱 iPhone/Android (MP4)</option>
                    <option value="audio_only">🎧 Âm thanh (MP3)</option>
                </select>
            </div>
            <button class="btn-main" onclick="startTask()" id="startBtn">Bắt đầu tải</button>
        </div>

        <div id="statusArea">
            <div class="spinner"></div>
            <div class="status-text" id="statusMsg">Đang kết nối...</div>
        </div>

        <div id="resultArea">
            <div style="margin-bottom: 10px; color: #34c759; font-weight: bold;">✅ Hoàn tất!</div>
            <a href="#" id="saveLink" class="btn-save" download>📥 LƯU VIDEO</a>
            <div class="ios-note" id="iosHint">💡 <b>iPhone:</b> Bấm nút trên, chọn "Lưu vào Tệp".</div>
            <button onclick="location.reload()" style="background:none; border:none; color:#007aff; margin-top:15px; cursor:pointer;">Tải file khác</button>
        </div>
    </div>

    <script>
        if (/iPad|iPhone|iPod/.test(navigator.userAgent)) document.getElementById('iosHint').style.display = 'block';

        async function startTask() {
            const url = document.getElementById('url').value;
            const mode = document.getElementById('mode').value;
            if (!url) return alert("Chưa nhập link!");

            document.getElementById('inputArea').style.opacity = '0.5';
            document.getElementById('startBtn').disabled = true;
            document.getElementById('statusArea').style.display = 'block';

            const formData = new FormData();
            formData.append('url', url);
            formData.append('mode', mode);

            try {
                const res = await fetch('/start_download', { method: 'POST', body: formData });
                const data = await res.json();
                pollStatus(data.task_id);
            } catch (err) { alert("Lỗi: " + err); location.reload(); }
        }

        function pollStatus(taskId) {
            const interval = setInterval(async () => {
                try {
                    const res = await fetch(`/check_status/${taskId}`);
                    const data = await res.json();
                    
                    if (data.status === 'processing') {
                        document.getElementById('statusMsg').innerText = data.message;
                    } else if (data.status === 'done') {
                        clearInterval(interval);
                        document.getElementById('statusArea').style.display = 'none';
                        document.getElementById('resultArea').style.display = 'block';
                        document.getElementById('saveLink').href = `/get_file/${data.filename}`;
                    } else if (data.status === 'error') {
                        clearInterval(interval);
                        alert(data.message);
                        location.reload();
                    }
                } catch (e) {}
            }, 1000);
        }
    </script>
</body>
</html>
"""

def download_worker(task_id, url, mode):
    try:
        save_status(task_id, {'status': 'processing', 'message': 'Đang kết nối Server...'})
        
        # Dọn dẹp file cũ
        for f in glob.glob(f'{TMP_DIR}/*'):
            try:
                if os.path.isfile(f) and time.time() - os.path.getmtime(f) > 1800: os.remove(f)
            except: pass

        ydl_opts = {
            'outtmpl': f'{TMP_DIR}/%(title).50s_{task_id}.%(ext)s',
            'trim_file_name': 50,
            'restrictfilenames': True,
            'noplaylist': True,
            'cookiefile': 'cookies.txt',
            'ffmpeg_location': '/usr/bin/ffmpeg',
            'quiet': True,
            'retries': 5,
            # Tự động fix lỗi nếu file bị kẹt ở .part
            'fixup': 'detect_or_warn', 
            'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        }

        if mode == 'mp4_convert':
            save_status(task_id, {'status': 'processing', 'message': 'Đang tải và Convert MP4...'})
            ydl_opts.update({
                'format': 'best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
                'merge_output_format': 'mp4',
                'postprocessor_args': ['-preset', 'ultrafast'],
            })
        elif mode == 'audio_only':
            save_status(task_id, {'status': 'processing', 'message': 'Đang tách nhạc...'})
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}],
            })
        else:
            save_status(task_id, {'status': 'processing', 'message': 'Đang tải chất lượng cao...'})
            ydl_opts.update({
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': 'mkv',
                'postprocessor_args': ['-preset', 'ultrafast'],
            })

        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # --- LOGIC TÌM FILE THÔNG MINH (CỨU FILE .PART) ---
        search_pattern = f'{TMP_DIR}/*{task_id}*'
        found_files = glob.glob(search_pattern)
        
        # 1. Tìm file hoàn chỉnh trước
        valid_files = [f for f in found_files if not f.endswith('.part') and not f.endswith('.ytdl') and not f.endswith('.json')]
        
        if valid_files:
            filename = os.path.basename(valid_files[0])
            save_status(task_id, {'status': 'done', 'filename': filename})
        else:
            # 2. Nếu không có file hoàn chỉnh, tìm file .part để đổi tên cứu dữ liệu
            part_files = [f for f in found_files if f.endswith('.part')]
            if part_files:
                part_file = part_files[0]
                new_name = part_file.replace('.part', '') # Xóa đuôi .part
                try:
                    os.rename(part_file, new_name)
                    save_status(task_id, {'status': 'done', 'filename': os.path.basename(new_name)})
                except Exception as e:
                    save_status(task_id, {'status': 'error', 'message': f'Lỗi đổi tên file: {str(e)}'})
            else:
                # In ra danh sách file tìm thấy để debug
                save_status(task_id, {'status': 'error', 'message': f'Lỗi: Không tìm thấy file. (Found: {str(found_files)})'})

    except Exception as e:
        save_status(task_id, {'status': 'error', 'message': f'Lỗi hệ thống: {str(e)}'})

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/start_download', methods=['POST'])
def start_download():
    task_id = uuid.uuid4().hex
    url = request.form.get('url')
    mode = request.form.get('mode')
    thread = threading.Thread(target=download_worker, args=(task_id, url, mode))
    thread.start()
    return jsonify({'task_id': task_id})

@app.route('/check_status/<task_id>')
def check_status(task_id):
    status = load_status(task_id)
    if status: return jsonify(status)
    return jsonify({'status': 'error', 'message': 'Đang đợi Server...'})

@app.route('/get_file/<filename>')
def get_file(filename):
    return send_file(os.path.join(TMP_DIR, filename), as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
