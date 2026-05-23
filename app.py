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
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Đăng Nhập - Pháp Môn Tâm Linh</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" href="{{ url_for('static', filename='logo.png') }}" type="image/png">
    
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        paper: '#F9F7F2',
                        ink: '#5D2E2E',
                        clay: '#8C4A4A',
                        clayHover: '#7A3E3E',
                    },
                    fontFamily: {
                        sans: ['Inter', 'sans-serif'],
                        mono: ['JetBrains Mono', 'monospace'],
                    },
                    boxShadow: {
                        'paper': '0 4px 20px -2px rgba(93, 46, 46, 0.1)',
                        'float': '0 10px 30px -5px rgba(140, 74, 74, 0.4)',
                    }
                }
            }
        }
    </script>
</head>
<body class="bg-paper text-ink font-sans min-h-screen flex items-center justify-center p-4">
    <div class="w-full max-w-md bg-white rounded-3xl shadow-paper p-8 md:p-10 relative overflow-hidden">
        <div class="absolute top-0 left-0 w-full h-2 bg-clay"></div>
        
        <div class="text-center mb-8">
            <h2 class="text-2xl font-bold uppercase tracking-widest text-clay mb-2">Pháp Môn Tâm Linh</h2>
            <p class="text-ink/60 italic text-sm">Vui lòng đăng nhập để tiếp tục</p>
        </div>

        <form method="POST" class="space-y-6">
            <div class="space-y-2">
                <label class="text-sm font-semibold text-ink/80 ml-1">Email Thành Viên</label>
                <div class="relative">
                    <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                        <i class="fa-solid fa-envelope text-clay/50"></i>
                    </div>
                    <input type="email" name="email" 
                        class="w-full bg-paper border border-transparent focus:border-clay focus:bg-white focus:ring-0 rounded-xl py-3 pl-11 pr-4 text-ink placeholder-ink/30 transition-all duration-300 outline-none" 
                        placeholder="example@gmail.com" required>
                </div>
            </div>

            <button type="submit" 
                class="w-full bg-clay text-white font-bold py-4 rounded-2xl shadow-float hover:-translate-y-1 hover:bg-clayHover active:scale-95 transition-all duration-300 flex items-center justify-center gap-2">
                <span>Đăng Nhập</span>
                <i class="fa-solid fa-arrow-right"></i>
            </button>
        </form>

        {% if error %}
        <div class="mt-6 p-4 bg-red-50 border border-red-100 rounded-xl flex items-start gap-3 animate-pulse">
            <i class="fa-solid fa-circle-exclamation text-red-500 mt-1"></i>
            <p class="text-red-600 text-sm font-medium">{{ error }}</p>
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

# --- GIAO DIỆN CHÍNH ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <title>Pháp Môn Tâm Linh 心靈法門</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" href="{{ url_for('static', filename='logo.png') }}" type="image/png">

    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #F9F7F2; }
        ::-webkit-scrollbar-thumb { background: #8C4A4A; border-radius: 10px; }
    </style>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        paper: '#F9F7F2',
                        ink: '#5D2E2E',
                        clay: '#8C4A4A',
                        clayHover: '#7A3E3E',
                    },
                    fontFamily: {
                        sans: ['Inter', 'sans-serif'],
                        mono: ['JetBrains Mono', 'monospace'],
                    },
                    boxShadow: {
                        'paper': '0 4px 20px -2px rgba(93, 46, 46, 0.1)',
                        'float': '0 10px 30px -5px rgba(140, 74, 74, 0.4)',
                    }
                }
            }
        }
    </script>
</head>
<body class="bg-paper text-ink font-sans min-h-screen py-8 px-4 flex justify-center items-start">
    
    <div class="w-full max-w-2xl">
        <div class="flex justify-between items-center mb-8 px-2">
            <div class="w-14 h-14 bg-white rounded-full shadow-float flex items-center justify-center overflow-hidden border-2 border-clay/10 p-1">
                <img src="{{ url_for('static', filename='logo.png') }}" alt="Logo" class="w-full h-full object-cover rounded-full">
            </div>
            
            <a href="/logout" class="group flex items-center gap-2 px-4 py-2 bg-white rounded-full shadow-sm hover:shadow-md transition-all duration-300">
                <span class="text-xs font-semibold text-ink/70 group-hover:text-clay">Thoát</span>
                <i class="fa-solid fa-arrow-right-from-bracket text-clay text-sm"></i>
            </a>
        </div>

        <div class="bg-white rounded-3xl shadow-paper p-6 md:p-10 relative">
            <div class="text-center mb-10">
                <h2 class="text-3xl font-bold text-ink mb-2 tracking-tight">Pháp Môn Tâm Linh</h2>
                <p class="text-clay font-serif italic text-lg">心靈法門</p>
            </div>

            <div class="space-y-6">
                <div class="relative group">
                    <input type="text" id="url" 
                        class="w-full bg-paper border-2 border-transparent focus:border-clay/30 rounded-2xl py-4 pl-12 pr-24 text-ink placeholder-ink/40 font-medium outline-none transition-all duration-300"
                        placeholder="Dán liên kết YouTube/Facebook...">
                    <div class="absolute left-4 top-1/2 -translate-y-1/2 text-clay/60">
                        <i class="fa-solid fa-link"></i>
                    </div>
                    <div class="absolute right-2 top-1/2 -translate-y-1/2 flex gap-1">
                        <button onclick="pasteLink()" class="p-2 hover:bg-white rounded-xl text-xs font-bold text-clay transition-colors" title="Dán">
                            DÁN
                        </button>
                        <button onclick="clearLink()" class="p-2 hover:bg-white rounded-xl text-xs font-bold text-ink/40 hover:text-red-500 transition-colors" title="Xóa">
                            <i class="fa-solid fa-xmark text-lg"></i>
                        </button>
                    </div>
                </div>

                <div class="relative">
                    <div class="absolute left-4 top-1/2 -translate-y-1/2 text-clay/60 z-10">
                        <i class="fa-solid fa-sliders"></i>
                    </div>
                    <select id="mode" class="w-full bg-paper border-r-[16px] border-transparent rounded-2xl py-4 pl-12 text-ink font-medium outline-none appearance-none cursor-pointer hover:bg-paper/80 transition-colors relative z-0">
                        <option value="mp4_convert">📱 Tải Video (MP4 - Tương thích cao)</option>
                        <option value="audio_only">🎧 Tải Âm Thanh (MP3 - Nghe đài)</option>
                    </select>
                </div>

                <button id="submitBtn" onclick="startDownload()" 
                    class="w-full bg-clay text-white text-lg font-bold py-5 rounded-2xl shadow-float hover:-translate-y-1 hover:bg-clayHover active:scale-95 disabled:opacity-70 disabled:cursor-not-allowed disabled:transform-none transition-all duration-300 flex items-center justify-center gap-3">
                    <i class="fa-solid fa-cloud-arrow-down"></i>
                    <span>Bắt Đầu Tải Về</span>
                </button>
            </div>

            <div id="progressArea" class="hidden mt-8 p-6 bg-paper rounded-2xl border border-clay/10">
                <div class="flex justify-between items-end mb-2">
                    <span class="text-xs font-bold text-clay uppercase tracking-wider">Tiến độ</span>
                    <span id="statusText" class="text-xs font-mono text-ink/70">Đang kết nối...</span>
                </div>
                <div class="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
                    <div id="progressBar" class="bg-clay h-2.5 rounded-full transition-all duration-500" style="width: 0%"></div>
                </div>
            </div>

            <div id="downloadArea" class="hidden mt-8 text-center animate-bounce-in">
                <div class="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-full text-green-600 mb-4 shadow-sm">
                    <i class="fa-solid fa-check text-2xl"></i>
                </div>
                <h3 class="text-xl font-bold text-ink mb-6">Xử lý hoàn tất!</h3>
                <a href="#" id="finalLink" onclick="resetUI()" 
                    class="inline-flex items-center gap-2 bg-ink text-white px-8 py-3 rounded-xl font-semibold shadow-lg hover:bg-clay transition-all duration-300">
                    <i class="fa-solid fa-download"></i>
                    <span>Lưu File Về Máy</span>
                </a>
            </div>

            <div id="errorText" class="hidden mt-6 p-4 bg-red-50 text-red-700 text-sm rounded-xl border border-red-100 text-center font-medium"></div>

            <div class="mt-10 text-center">
                <p class="text-xs text-ink/40 font-serif italic">• Bình An & Tiện Lợi •</p>
            </div>
        </div>
    </div>

    <script>
        async function pasteLink() { 
            try { 
                const text = await navigator.clipboard.readText();
                document.getElementById('url').value = text; 
            } catch (err) { 
                alert('Vui lòng dán thủ công.'); 
            } 
        }

        function clearLink() { 
            document.getElementById('url').value = ''; 
            resetUIState();
        }

        function resetUIState() {
            document.getElementById('progressArea').classList.add('hidden');
            document.getElementById('downloadArea').classList.add('hidden');
            document.getElementById('errorText').classList.add('hidden');
            const btn = document.getElementById('submitBtn');
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-cloud-arrow-down"></i><span>Bắt Đầu Tải Về</span>';
        }

        function resetUI() { 
            setTimeout(() => { clearLink(); }, 3000); 
        }

        async function startDownload() {
            const url = document.getElementById('url').value;
            const mode = document.getElementById('mode').value;
            
            if (!url) return alert("Vui lòng dán liên kết video!");
            
            const btn = document.getElementById('submitBtn');
            const progressArea = document.getElementById('progressArea');
            const progressBar = document.getElementById('progressBar');
            const statusText = document.getElementById('statusText');
            const downloadArea = document.getElementById('downloadArea');
            const errorText = document.getElementById('errorText');

            downloadArea.classList.add('hidden');
            errorText.classList.add('hidden');
            progressArea.classList.remove('hidden');
            
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i><span>Đang xử lý...</span>';
            progressBar.style.width = '5%';
            statusText.innerText = 'Đang khởi động server...';

            const formData = new FormData(); 
            formData.append('url', url); 
            formData.append('mode', mode);

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
                            }
                            else if (data.status === 'merging') { 
                                progressBar.style.width = '98%'; 
                                statusText.innerText = 'Đang ghép file...'; 
                            }
                            else if (data.status === 'finished') { 
                                progressBar.style.width = '100%'; 
                                statusText.innerText = 'Hoàn tất!'; 
                                document.getElementById('finalLink').href = '/get_file/' + encodeURIComponent(data.filename); 
                                downloadArea.classList.remove('hidden');
                                progressArea.classList.add('hidden');
                                btn.innerHTML = '<i class="fa-solid fa-rotate-right"></i><span>Tải File Khác</span>';
                                btn.disabled = false; 
                            }
                            else if (data.status === 'error') { throw new Error(data.message); }
                        } catch (err) { if (err.message && !err.message.includes("JSON")) throw err; }
                    }
                }
            } catch (error) { 
                errorText.innerText = "Lỗi: " + error.message; 
                errorText.classList.remove('hidden');
                btn.disabled = false; 
                btn.innerHTML = 'Thử Lại';
                progressArea.classList.add('hidden'); 
            }
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

        # --- CẤU HÌNH FIX LỖI "FILE NAME TOO LONG" VÀ THÊM COOKIES ---
        ydl_opts = {
            'outtmpl': '/tmp/%(title).30s-%(id)s.%(ext)s',
            'restrictfilenames': False,
            'noplaylist': True,
            'ffmpeg_location': '/usr/bin/ffmpeg',
            'quiet': True,
            'progress_hooks': [progress_hook],
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            },
            # THÊM DÒNG NÀY ĐỂ ĐỌC COOKIES TỪ DOCKER VOLUME
            'cookiefile': '/app/cookies.txt'
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

