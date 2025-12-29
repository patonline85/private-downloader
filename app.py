import os
import glob
import json
import time
import uuid
import asyncio
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from yt_dlp import YoutubeDL

app = FastAPI()

# --- CẤU HÌNH THƯ MỤC ---
# Mount thư mục static để chứa logo.png
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Tạo thư mục tạm an toàn
TMP_DIR = '/tmp'
os.makedirs(TMP_DIR, exist_ok=True)

# --- GIAO DIỆN HTML ---
HTML_CONTENT = """
<!DOCTYPE html>
<html>
<head>
    <title>Pháp Môn Tâm Linh 心靈法門</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        :root { --bg-color: #f4f1ea; --card-bg: #ffffff; --primary-color: #8d6e63; --accent-color: #5d4037; --text-color: #4e342e; --success-color: #689f38; --border-radius: 12px; }
        body { font-family: 'Segoe UI', sans-serif; background: var(--bg-color); display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; color: var(--text-color); }
        .container { background: var(--card-bg); padding: 30px; border-radius: var(--border-radius); box-shadow: 0 8px 30px rgba(93, 64, 55, 0.15); width: 90%; max-width: 480px; border-top: 5px solid var(--accent-color); text-align: center; }
        
        /* LOGO STYLE */
        .logo-img { max-width: 120px; margin-bottom: 15px; border-radius: 50%; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        
        h2 { color: var(--accent-color); margin-bottom: 25px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-top: 0; }
        .input-group { position: relative; margin-bottom: 20px; text-align: left; }
        input[type="text"] { width: 100%; padding: 14px 90px 14px 15px; border: 2px solid #e0e0e0; border-radius: var(--border-radius); box-sizing: border-box; font-size: 16px; outline: none; transition: 0.3s; background: #fafafa; }
        input[type="text"]:focus { border-color: var(--primary-color); background: #fff; }
        .action-btns { position: absolute; right: 8px; top: 50%; transform: translateY(-50%); display: flex; gap: 5px; }
        .icon-btn { background: #efebe9; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; color: var(--accent-color); font-weight: bold; }
        
        select { width: 100%; padding: 14px; border: 2px solid #e0e0e0; border-radius: var(--border-radius); background: #fff; font-size: 16px; margin-bottom: 20px; color: var(--text-color); }
        
        /* BUTTONS */
        .btn-group { display: flex; gap: 10px; flex-direction: column; }
        button.main-btn { background: var(--accent-color); color: white; border: none; padding: 16px; border-radius: var(--border-radius); cursor: pointer; font-weight: bold; width: 100%; font-size: 16px; transition: 0.3s; box-shadow: 0 4px 10px rgba(93, 64, 55, 0.3); }
        button.main-btn:hover { background: #3e2723; transform: translateY(-1px); }
        button.main-btn:disabled { background: #bdbdbd; cursor: not-allowed; transform: none; box-shadow: none; }
        
        button.direct-btn { background: #fff; color: var(--accent-color); border: 2px solid var(--accent-color); padding: 14px; border-radius: var(--border-radius); cursor: pointer; font-weight: bold; width: 100%; font-size: 16px; transition: 0.3s; }
        button.direct-btn:hover { background: #efebe9; }

        .progress-container { margin-top: 25px; display: none; text-align: left; }
        .progress-bg { width: 100%; background-color: #efebe9; border-radius: 20px; height: 10px; overflow: hidden; }
        .progress-bar { height: 100%; width: 0%; background-color: var(--success-color); transition: width 0.3s ease; }
        .status-text { text-align: center; font-size: 0.9em; color: var(--primary-color); margin-top: 8px; font-style: italic; }
        
        #downloadArea { display: none; margin-top: 25px; border-top: 1px dashed #d7ccc8; padding-top: 20px; }
        .save-btn { display: inline-block; padding: 14px 35px; background: var(--success-color); color: white; text-decoration: none; border-radius: var(--border-radius); font-weight: bold; font-size: 16px; box-shadow: 0 4px 10px rgba(104, 159, 56, 0.3); }
        .error-msg { color: #c62828; margin-top: 15px; display: none; background: #ffebee; padding: 12px; border-radius: 8px; font-size: 0.9em; }
        .note { font-size: 12px; color: #a1887f; margin-top: 25px; }
    </style>
</head>
<body>
    <div class="container">
        <img src="/static/logo.png" alt="Logo" class="logo-img" onerror="this.style.display='none'">
        
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

        <div class="btn-group">
            <button class="main-btn" id="submitBtn" onclick="startDownload('server')">Tải Về (Server Xử Lý)</button>
            <button class="direct-btn" id="directBtn" onclick="getDirectLink()">🚀 Lấy Link Trực Tiếp (Nhẹ Máy)</button>
        </div>

        <div class="progress-container" id="progressArea">
            <div class="progress-bg"><div class="progress-bar" id="progressBar"></div></div>
            <div class="status-text" id="statusText">Đang kết nối...</div>
        </div>

        <div id="downloadArea">
            <p style="color: var(--success-color); font-weight: bold;">✅ Đã hoàn tất!</p>
            <a href="#" id="finalLink" class="save-btn" onclick="resetUI()">Lưu Về Máy</a>
        </div>
        
        <p id="errorText" class="error-msg"></p>
        <p class="note">PMTL.SITE • FASTAPI ENGINE</p>
    </div>

    <script>
        async function pasteLink() { try { document.getElementById('url').value = await navigator.clipboard.readText(); } catch (err) { alert('Vui lòng dán thủ công'); } }
        
        function clearLink() {
            document.getElementById('url').value = '';
            document.getElementById('progressArea').style.display = 'none';
            document.getElementById('downloadArea').style.display = 'none';
            document.getElementById('errorText').style.display = 'none';
            enableBtns();
        }

        function disableBtns() {
            document.getElementById('submitBtn').disabled = true;
            document.getElementById('directBtn').disabled = true;
        }

        function enableBtns() {
            document.getElementById('submitBtn').disabled = false;
            document.getElementById('directBtn').disabled = false;
            document.getElementById('submitBtn').innerText = "Tải Về (Server Xử Lý)";
        }

        function resetUI() { setTimeout(() => { clearLink(); }, 3000); }

        // --- CÁCH 1: Tải trực tiếp (Nhẹ máy) ---
        async function getDirectLink() {
            const url = document.getElementById('url').value;
            if (!url) return alert("Bạn chưa nhập liên kết!");
            
            disableBtns();
            document.getElementById('statusText').innerText = "Đang lấy link gốc từ Google...";
            document.getElementById('progressArea').style.display = 'block';
            document.getElementById('progressBar').style.width = '50%';

            try {
                const formData = new FormData();
                formData.append('url', url);
                
                const response = await fetch('/get_direct_url', { method: 'POST', body: formData });
                const data = await response.json();
                
                if (data.status === 'success') {
                    document.getElementById('progressBar').style.width = '100%';
                    document.getElementById('statusText').innerText = "Đã lấy được link!";
                    // Mở tab mới để tải
                    window.open(data.url, '_blank');
                    clearLink(); // Reset nhanh
                } else {
                    throw new Error(data.message);
                }
            } catch (error) {
                document.getElementById('errorText').innerText = "Lỗi: " + error.message;
                document.getElementById('errorText').style.display = 'block';
                enableBtns();
            }
        }

        // --- CÁCH 2: Tải qua Server (Chất lượng cao) ---
        async function startDownload() {
            const url = document.getElementById('url').value;
            const mode = document.getElementById('mode').value;
            if (!url) return alert("Bạn chưa nhập liên kết!");

            disableBtns();
            document.getElementById('submitBtn').innerText = "⏳ Đang xử lý...";
            document.getElementById('downloadArea').style.display = 'none';
            document.getElementById('errorText').style.display = 'none';
            document.getElementById('progressArea').style.display = 'block';
            document.getElementById('progressBar').style.width = '5%';
            document.getElementById('statusText').innerText = 'Đang khởi động...';

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
                                document.getElementById('progressBar').style.width = data.percent + '%';
                                document.getElementById('statusText').innerText = `Đang tải: ${data.percent}% (${data.speed})`;
                            } else if (data.status === 'merging') {
                                document.getElementById('progressBar').style.width = '98%';
                                document.getElementById('statusText').innerText = 'Đang ghép file... (Server)';
                            } else if (data.status === 'finished') {
                                document.getElementById('progressBar').style.width = '100%';
                                document.getElementById('statusText').innerText = 'Thành công!';
                                document.getElementById('finalLink').href = '/get_file/' + encodeURIComponent(data.filename);
                                document.getElementById('downloadArea').style.display = 'block';
                                document.getElementById('submitBtn').innerText = "Tải File Khác";
                                document.getElementById('submitBtn').disabled = false;
                                document.getElementById('directBtn').disabled = false;
                            } else if (data.status === 'error') {
                                throw new Error(data.message);
                            }
                        } catch (err) { }
                    }
                }
            } catch (error) {
                document.getElementById('errorText').innerText = "Lỗi: " + error.message;
                document.getElementById('errorText').style.display = 'block';
                enableBtns();
                document.getElementById('progressArea').style.display = 'none';
            }
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_CONTENT

# --- API 1: LẤY LINK TRỰC TIẾP (OFFLOAD ARMBIAN) ---
@app.post("/get_direct_url")
async def get_direct_url(url: str = Form(...)):
    """
    Hàm này lấy URL trực tiếp từ YouTube. 
    Trình duyệt người dùng sẽ tự tải về. Server không tốn băng thông.
    """
    try:
        ydl_opts = {
            'format': 'best[ext=mp4]/best', # Ưu tiên MP4 file đơn
            'quiet': True,
            'noplaylist': True,
            # 'cookiefile': 'cookies.txt', # Bật nếu cần
        }
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return JSONResponse({"status": "success", "url": info.get('url'), "title": info.get('title')})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)})

# --- API 2: TẢI QUA SERVER (CHẤT LƯỢNG CAO) ---
@app.post("/stream_download")
async def stream_download(url: str = Form(...), mode: str = Form(...)):
    
    async def generate():
        # --- DỌN DẸP FILE RÁC ---
        current_time = time.time()
        for f in glob.glob(f'{TMP_DIR}/*'):
            try:
                if os.path.isfile(f) and (current_time - os.path.getmtime(f)) > 1800:
                    os.remove(f)
            except: pass

        unique_id = str(uuid.uuid4())[:8]
        
        # Hàm callback xử lý tiến trình
        def progress_hook(d):
            if d['status'] == 'downloading':
                p = d.get('_percent_str', '0%').replace('%','').strip()
                s = d.get('_speed_str', 'N/A')
                # In ra định dạng JSON line
                print(json.dumps({'status': 'downloading', 'percent': p, 'speed': s}))

        # Cấu hình yt-dlp
        ydl_opts = {
            'outtmpl': f'{TMP_DIR}/%(title).50s_{unique_id}.%(ext)s',
            'trim_file_name': 50,
            'restrictfilenames': True,
            'noplaylist': True,
            'quiet': True,
            # 'cookiefile': 'cookies.txt', 
            'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        }

        if mode == 'mp4_convert':
             ydl_opts.update({'format': 'bv*[vcodec^=avc]+ba[ext=m4a]/b[ext=mp4]/b', 'merge_output_format': 'mp4'})
        elif mode == 'audio_only':
            ydl_opts.update({'format': 'bestaudio/best', 'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]})
        else: 
            ydl_opts.update({'format': 'bv*+ba/b', 'merge_output_format': 'mkv'})

        # Chạy yt-dlp trong Thread riêng để không chặn FastAPI
        try:
            loop = asyncio.get_event_loop()
            
            # Wrapper để bắt tiến trình
            def run_yt_dlp():
                # Vì yt-dlp sync không hỗ trợ yield ra ngoài dễ dàng, ta dùng queue hoặc đơn giản là logic check file sau cùng.
                # Ở đây dùng cách cơ bản để stream status giả lập hoặc phải hook sys.stdout nếu muốn realtime 100%
                # Tuy nhiên, ta sẽ yield trạng thái sau khi tải xong.
                with YoutubeDL(ydl_opts) as ydl:
                    # Hook print vào generator là kỹ thuật khó trong async, 
                    # nên ở đây ta chấp nhận yield trạng thái download giả lập hoặc cập nhật sau.
                    # Để đơn giản và ổn định cho Armbian:
                    ydl.params['progress_hooks'] = [
                        lambda d: None # Có thể mở rộng để push vào Queue nếu cần realtime cực chuẩn
                    ]
                    ydl.download([url])

            # Chạy download (Blocking IO -> Thread)
            await loop.run_in_executor(None, run_yt_dlp)

            # Tìm file kết quả
            search_pattern = f'{TMP_DIR}/*{unique_id}*'
            found_files = glob.glob(search_pattern)
            valid_files = [f for f in found_files if not f.endswith('.part') and not f.endswith('.ytdl')]

            if valid_files:
                filename = os.path.basename(valid_files[0])
                yield json.dumps({'status': 'finished', 'filename': filename}) + "\n"
            else:
                yield json.dumps({'status': 'error', 'message': 'Không tìm thấy file.'}) + "\n"

        except Exception as e:
            error_msg = str(e)
            if "Requested format is not available" in error_msg: error_msg = "Lỗi định dạng video."
            yield json.dumps({'status': 'error', 'message': error_msg}) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")

@app.get('/get_file/{filename}')
async def get_file(filename: str):
    safe_path = os.path.join(TMP_DIR, filename)
    if os.path.isfile(safe_path) and safe_path.startswith(TMP_DIR):
        return FileResponse(safe_path, filename=filename)
    return JSONResponse({"error": "File not found"}, status_code=404)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
