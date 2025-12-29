import os
import glob
import json
import time
from flask import Flask, render_template_string, request, send_file, Response, stream_with_context, session, redirect, url_for
from yt_dlp import YoutubeDL
import gspread
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)

# --- CẤU HÌNH BẢO MẬT & SHEET ---
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'phap_mon_tam_linh_secret_key_999')
SHEET_ID = os.environ.get('GOOGLE_SHEET_ID')
SHEET_TAB_NAME = 'Users'

def get_allowed_emails():
    """Kết nối Google Sheet và lấy danh sách email được phép"""
    try:
        if not SHEET_ID:
            print("Lỗi: Chưa cấu hình biến môi trường GOOGLE_SHEET_ID")
            return []

        private_key = os.environ.get('GOOGLE_PRIVATE_KEY', '').replace('\\n', '\n')
        client_email = os.environ.get('GOOGLE_SERVICE_ACCOUNT_EMAIL', '')
        
        if not private_key or not client_email:
            print("Lỗi: Thiếu biến môi trường Key hoặc Email Service Account")
            return []

        creds_dict = {
            "type": "service_account",
            "project_id": "generic-project",
            "private_key_id": "generic-key-id",
            "private_key": private_key,
            "client_email": client_email,
            "client_id": "generic-client-id",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{client_email}"
        }

        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        sheet = client.open_by_key(SHEET_ID).worksheet(SHEET_TAB_NAME)
        emails = sheet.col_values(1)
        return [e.strip().lower() for e in emails if '@' in e]
    except Exception as e:
        print(f"Lỗi kết nối Google Sheet: {str(e)}")
        return []

# --- HÀM DỌN DẸP THÔNG MINH (CHỈ XÓA FILE CŨ > 60 PHÚT) ---
def cleanup_old_files():
    folder = '/tmp'
    now = time.time()
    # Thời gian sống của file: 60 phút (3600 giây)
    retention_period = 3600 
    
    for f in glob.glob(os.path.join(folder, '*')):
        try:
            # Nếu file cũ hơn 60 phút thì mới xóa
            if os.path.isfile(f) and os.stat(f).st_mtime < now - retention_period:
                os.remove(f)
        except Exception:
            pass

# --- GIAO DIỆN ĐĂNG NHẬP ---
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Đăng Nhập - Pháp Môn Tâm Linh</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, interactive-widget=resizes-content">
    <style>
        :root { --bg-color: #f4f1ea; --card-bg: #ffffff; --accent-color: #5d4037; --text-color: #4e342e; --border-radius: 12px; }
        body { font-family: 'Segoe UI', sans-serif; background: var(--bg-color); display: flex; justify-content: center; align-items: center; min-height: 100dvh; margin: 0; color: var(--text-color); }
        .container { background: var(--card-bg); padding: 40px 30px; border-radius: var(--border-radius); box-shadow: 0 8px 30px rgba(93, 64, 55, 0.15); width: 90%; max-width: 400px; border-top: 5px solid var(--accent-color); text-align: center; }
        h2 { color: var(--accent-color); margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px; }
        .sub-title { font-size: 14px; color: #8d6e63; margin-bottom: 30px; font-style: italic; }
        input { width: 100%; padding: 14px; border: 2px solid #e0e0e0; border-radius: var(--border-radius); box-sizing: border-box; font-size: 16px; margin-bottom: 20px; outline: none; background: #fafafa; }
        input:focus { border-color: var(--accent-color); background: #fff; }
        button { background: var(--accent-color); color: white; border: none; padding: 16px; border-radius: var(--border-radius); cursor: pointer; font-weight: bold; width: 100%; font-size: 16px; transition: 0.3s; box-shadow: 0 4px 10px rgba(93, 64, 55, 0.3); }
        button:hover { background: #3e2723; transform: translateY(-1px); }
        .error { color: #c62828; margin-top: 15px; background: #ffebee; padding: 10px; border-radius: 8px; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Pháp Môn Tâm Linh</h2>
        <p class="sub-title">Vui lòng đăng nhập để tiếp tục</p>
        <form method="POST">
            <input type="email" name="email" placeholder="Nhập địa chỉ Email..." required>
            <button type="submit">Đăng Nhập</button>
        </form>
        {% if error %}
        <div class="error">{{ error }}</div>
        {% endif %}
    </div>
</body>
</html>
"""

# --- GIAO DIỆN CHÍNH ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Pháp Môn Tâm Linh 心靈法門</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, interactive-widget=resizes-content">
    <style>
        :root {
            --bg-color: #f4f1ea; --card-bg: #ffffff; --primary-color: #8d6e63; --accent-color: #5d4037; --text-color: #4e342e; --success-color: #689f38; --border-radius: 12px;
        }
        body { 
            font-family: 'Segoe UI', sans-serif; background: var(--bg-color); display: flex; justify-content: center; align-items: flex-start; min-height: 100dvh; margin: 0; color: var(--text-color); padding-top: 40px; box-sizing: border-box;
        }
        .container { 
            background: var(--card-bg); padding: 30px; border-radius: var(--border-radius); box-shadow: 0 8px 30px rgba(93, 64, 55, 0.15); width: 90%; max-width: 480px; border-top: 5px solid var(--accent-color); margin-bottom: 40px; 
        }
        .header-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .logo-wrapper { flex-grow: 1; text-align: center; } 
        .logout-btn { font-size: 12px; color: #a1887f; text-decoration: none; border: 1px solid #d7ccc8; padding: 4px 10px; border-radius: 15px; transition: 0.2s; }
        .logout-btn:hover { background: #efebe9; color: var(--accent-color); }
        .spacer { width: 50px; } 

        .logo-img { max-width: 100px; height: auto; border-radius: 50%; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
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
        <div class="header-row">
            <div class="spacer"></div>
            <div class="logo-wrapper">
                <img src="{{ url_for('static', filename='logo.png') }}" alt="Logo" class="logo-img">
            </div>
            <a href="/logout" class="logout-btn">Thoát</a>
        </div>
        <h2>Pháp Môn Tâm Linh 心靈法門</h2>
        
        <div class="input-group">
            <input type="text" id="url" placeholder="Dán liên kết vào đây..." required>
            <div class="action-btns">
                <button type="button" class="icon-btn" onclick="pasteLink()">Dán</button>
                <button type="button" class="icon-btn" onclick="clearLink()">Xóa</button>
            </div>
        </div>
        <select id="mode">
            <option value="mp4_convert">📱 Tải Video (MP4 - Xem trên mọi thiết bị)</option>
            <option value="audio_only">🎧 Tải Âm Thanh (MP3 - Nghe đài)</option>
        </select>
        <button id="submitBtn" onclick="startDownload()">Bắt Đầu Tải Về</button>
        <div class="progress-container" id="progressArea">
            <div class="progress-bg">
                <div class="progress-bar" id="progressBar"></div>
            </div>
            <div class="status-text" id="statusText">Đang kết nối...</div>
        </div>
        <div id="downloadArea">
            <p style="color: var(--success-color); font-weight: bold;">✅ Đã hoàn tất!</p>
            <a href="#" id="finalLink" class="save-btn" onclick="resetUI()">Lưu Về Máy</a>
        </div>
        <p id="errorText" class="error-msg"></p>
        <p class="note"> • Bình An & Tiện Lợi • </p>
    </div>
    <script>
        async function pasteLink() { try { document.getElementById('url').value = await navigator.clipboard.readText(); } catch (err) { alert('Vui lòng dán thủ công'); } }
        function clearLink() { document.getElementById('url').value = ''; document.getElementById('progressArea').style.display = 'none'; document.getElementById('downloadArea').style.display = 'none'; document.getElementById('errorText').style.display = 'none'; document.getElementById('submitBtn').disabled = false; }
        function resetUI() { setTimeout(() => { clearLink(); }, 3000); }
        async function startDownload() {
            const url = document.getElementById('url').value;
            const mode = document.getElementById('mode').value;
            if (!url) return alert("Bạn chưa nhập liên kết!");
            const btn = document.getElementById('submitBtn'); const progressArea = document.getElementById('progressArea'); const progressBar = document.getElementById('progressBar'); const statusText = document.getElementById('statusText'); const downloadArea = document.getElementById('downloadArea'); const errorText = document.getElementById('errorText');
            btn.disabled = true; btn.innerText = "⏳ Đang xử lý..."; downloadArea.style.display = 'none'; errorText.style.display = 'none'; progressArea.style.display = 'block'; progressBar.style.width = '5%'; statusText.innerText = 'Đang khởi động...';
            const formData = new FormData(); formData.append('url', url); formData.append('mode', mode);
            try {
                const response = await fetch('/stream_download', { method: 'POST', body: formData });
                const reader = response.body.getReader(); const decoder = new TextDecoder();
                while (true) {
                    const { value, done } = await reader.read(); if (done) break;
                    const chunk = decoder.decode(value); const lines = chunk.split('\\n');
                    for (const line of lines) {
                        if (!line.trim()) continue;
                        try {
                            const data = JSON.parse(line);
                            if (data.status === 'downloading') { progressBar.style.width = data.percent + '%'; statusText.innerText = `Đang tải: ${data.percent}% (${data.speed})`; }
                            else if (data.status === 'merging') { progressBar.style.width = '98%'; statusText.innerText = 'Đang ghép file... (Vui lòng đợi)'; }
                            else if (data.status === 'finished') { progressBar.style.width = '100%'; statusText.innerText = 'Thành công!'; document.getElementById('finalLink').href = '/get_file/' + encodeURIComponent(data.filename); downloadArea.style.display = 'block'; btn.innerText = "Tải File Khác"; btn.disabled = false; }
                            else if (data.status === 'error') { throw new Error(data.message); }
                        } catch (err) { if (err.message && !err.message.includes("JSON")) throw err; }
                    }
                }
            } catch (error) { errorText.innerText = "Lỗi: " + error.message; errorText.style.display = 'block'; btn.disabled = false; btn.innerText = "Thử Lại"; progressArea.style.display = 'none'; }
        }
    </script>
</body>
</html>
"""

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session: return redirect(url_for('index'))
    error = None
    if request.method == 'POST':
        email_input = request.form.get('email', '').strip().lower()
        if not email_input: error = "Vui lòng nhập địa chỉ email."
        else:
            allowed_users = get_allowed_emails()
            if not allowed_users: error = "Không kết nối được danh sách thành viên (Lỗi ID/Key)."
            elif email_input in allowed_users:
                session['user'] = email_input
                session.permanent = True
                return redirect(url_for('index'))
            else: error = "Email này chưa được cấp quyền truy cập."
    return render_template_string(LOGIN_TEMPLATE, error=error)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

@app.route('/', methods=['GET'])
def index():
    if 'user' not in session: return redirect(url_for('login'))
    return render_template_string(HTML_TEMPLATE)

@app.route('/stream_download', methods=['POST'])
def stream_download():
    if 'user' not in session:
         return Response(json.dumps({'status': 'error', 'message': 'Phiên đăng nhập hết hạn.'}), mimetype='application/json')

    url = request.form.get('url')
    mode = request.form.get('mode')

    def generate():
        # --- FIX LỖI CRITICAL: Chỉ xóa file cũ hơn 60 phút ---
        cleanup_old_files()

        def progress_hook(d):
            if d['status'] == 'downloading':
                p = d.get('_percent_str', '0%').replace('%','').strip()
                s = d.get('_speed_str', 'N/A')
                yield json.dumps({'status': 'downloading', 'percent': p, 'speed': s}) + "\n"
            elif d['status'] == 'finished':
                yield json.dumps({'status': 'merging'}) + "\n"

        ydl_opts = {
            'outtmpl': '/tmp/%(title)s.%(ext)s',
            # Vẫn giữ trim_file_name để tránh lỗi OS (Linux thường giới hạn 255 bytes)
            # 50 ký tự là an toàn tuyệt đối.
            'trim_file_name': 50,
            'restrictfilenames': False,
            'noplaylist': True,
            'ffmpeg_location': '/usr/bin/ffmpeg',
            'quiet': True,
            'progress_hooks': [progress_hook],
            'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        }

        if mode == 'mp4_convert':
             ydl_opts.update({'format': 'bv*[vcodec^=avc]+ba[ext=m4a]/b[ext=mp4]/b', 'merge_output_format': 'mp4'})
        elif mode == 'audio_only':
            ydl_opts.update({'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],})
        else: 
            ydl_opts.update({'format': 'bv*+ba/b', 'merge_output_format': 'mkv'})

        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            files = [f for f in glob.glob('/tmp/*') if not f.endswith(('.txt', '.part', '.ytdl'))]
            if files:
                # Lấy file mới nhất vừa tạo ra
                final_file = max(files, key=os.path.getctime)
                filename = os.path.basename(final_file)
                yield json.dumps({'status': 'finished', 'filename': filename}) + "\n"
            else:
                yield json.dumps({'status': 'error', 'message': 'Lỗi: Không tạo được file cuối cùng.'}) + "\n"
        except Exception as e:
            error_msg = str(e)
            if "Requested format is not available" in error_msg: error_msg = "Video này chặn tải chất lượng cao (DRM/IP). Đã thử tải SD nhưng thất bại."
            yield json.dumps({'status': 'error', 'message': error_msg}) + "\n"

    return Response(stream_with_context(generate()), mimetype='text/plain')

@app.route('/get_file/<filename>')
def get_file(filename):
    if 'user' not in session: return "Unauthorized", 401
    safe_path = os.path.join('/tmp', filename)
    if os.path.exists(safe_path):
        return send_file(safe_path, as_attachment=True)
    return "Not Found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
