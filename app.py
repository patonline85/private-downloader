import os
import glob
import json
import time
import subprocess
from flask import Flask, render_template_string, request, send_file, Response, stream_with_context, jsonify
from yt_dlp import YoutubeDL

# --- KHU VỰC CẤU HÌNH MÔI TRƯỜNG (CRITICAL FIX) ---
# Vì lệnh 'which node' của bạn trả về: /usr/bin/node
# Nên thư mục cần thêm vào PATH là: /usr/bin

# 1. Ép cứng thư mục /usr/bin vào biến môi trường PATH
if '/usr/bin' not in os.environ['PATH']:
    os.environ['PATH'] = '/usr/bin:' + os.environ['PATH']

print(f"✅ PATH FINAL: {os.environ['PATH']}")

# 2. Test thử xem Python gọi được Node chưa (để in ra log cho yên tâm)
try:
    # Gọi thẳng lệnh node -v để kiểm tra
    node_ver = subprocess.check_output(["node", "-v"], stderr=subprocess.STDOUT).decode().strip()
    print(f"🎉 SUCCESS: Python đã kết nối được NodeJS: {node_ver}")
except Exception as e:
    print(f"❌ ERROR: Python vẫn chưa gọi được Node. Lỗi: {str(e)}")
# --------------------------------------------------

app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Pro Video Selector</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: -apple-system, sans-serif; background: #121212; color: #e0e0e0; margin: 0; padding: 20px; }
        .container { max-width: 600px; margin: 0 auto; background: #1e1e1e; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
        h2 { text-align: center; margin-top: 0; color: #fff; }
        .input-group { display: flex; gap: 10px; margin-bottom: 20px; }
        input[type="text"] { flex: 1; padding: 12px; background: #2c2c2c; border: 1px solid #444; color: white; border-radius: 6px; }
        button { padding: 12px 20px; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; transition: 0.2s; }
        .btn-analyze { background: #0a84ff; color: white; }
        .btn-analyze:hover { background: #0077e6; }
        .btn-download { background: #30d158; color: white; width: 100%; font-size: 1.1em; margin-top: 20px; display: none; }
        #selectionArea { display: none; border-top: 1px solid #333; padding-top: 20px; }
        .section-title { font-size: 1.1em; color: #aaa; margin-bottom: 10px; border-bottom: 2px solid #444; display: inline-block; }
        .option-grid { display: grid; grid-template-columns: 1fr; gap: 8px; max-height: 250px; overflow-y: auto; margin-bottom: 20px; padding-right: 5px; }
        .radio-label { display: flex; align-items: center; background: #2a2a2a; padding: 10px; border-radius: 6px; cursor: pointer; border: 1px solid #333; }
        .radio-label:hover { background: #333; }
        .radio-label input { margin-right: 15px; transform: scale(1.2); }
        .info-main { font-weight: bold; color: white; }
        .info-sub { font-size: 0.85em; color: #888; margin-left: auto; }
        .badge { font-size: 0.75em; padding: 2px 6px; border-radius: 4px; margin-left: 8px; }
        .badge-mp4 { background: #005bb5; color: white; }
        .badge-webm { background: #d63384; color: white; }
        #progressArea { display: none; margin-top: 20px; }
        .progress-bg { background: #333; height: 10px; border-radius: 5px; overflow: hidden; }
        .progress-fill { background: #30d158; height: 100%; width: 0%; transition: width 0.3s; }
        .status-text { text-align: center; font-size: 0.9em; margin-top: 5px; color: #aaa; }
        #finalLinkArea { display: none; text-align: center; margin-top: 20px; }
        .save-btn { background: #ff9f0a; color: black; text-decoration: none; padding: 12px 30px; border-radius: 6px; font-weight: bold; display: inline-block; }
    </style>
</head>
<body>

<div class="container">
    <h2>🛠️ Youtube Selector</h2>
    <div class="input-group">
        <input type="text" id="url" placeholder="Dán link Youtube vào đây..." required>
        <button class="btn-analyze" id="btnAnalyze" onclick="analyzeVideo()">🔍 Phân tích</button>
    </div>

    <div id="selectionArea">
        <div class="section-title">🎞️ Chọn VIDEO</div>
        <div class="option-grid" id="videoList">Loading...</div>
        <div class="section-title">🎵 Chọn AUDIO</div>
        <div class="option-grid" id="audioList">Loading...</div>
        <button class="btn-download" id="btnDownload" onclick="startDownload()">⬇️ BẮT ĐẦU TẢI & GỘP</button>
    </div>

    <div id="progressArea">
        <div class="progress-bg"><div class="progress-fill" id="progressBar"></div></div>
        <div class="status-text" id="statusText">Đang xử lý...</div>
    </div>
    
    <div id="finalLinkArea">
        <a href="#" id="finalLink" class="save-btn">💾 Lưu Video Về Máy</a>
    </div>
</div>

<script>
    let currentUrl = "";

    async function analyzeVideo() {
        const url = document.getElementById('url').value;
        if(!url) return alert("Vui lòng nhập link!");
        currentUrl = url;
        const btn = document.getElementById('btnAnalyze');
        btn.innerText = "⏳ Đang lấy dữ liệu...";
        btn.disabled = true;
        document.getElementById('selectionArea').style.display = 'none';
        document.getElementById('finalLinkArea').style.display = 'none';

        try {
            const formData = new FormData();
            formData.append('url', url);
            const response = await fetch('/analyze', { method: 'POST', body: formData });
            const data = await response.json();
            if(data.error) { alert("Lỗi: " + data.error); btn.innerText = "🔍 Phân tích lại"; btn.disabled = false; return; }
            renderOptions(data.videos, data.audios);
            document.getElementById('selectionArea').style.display = 'block';
            document.getElementById('btnDownload').style.display = 'block';
            btn.innerText = "🔍 Phân tích xong";
            btn.disabled = false;
        } catch (e) { alert("Lỗi kết nối Server: " + e); btn.innerText = "🔍 Phân tích lại"; btn.disabled = false; }
    }

    function renderOptions(videos, audios) {
        const vList = document.getElementById('videoList');
        const aList = document.getElementById('audioList');
        vList.innerHTML = ""; aList.innerHTML = "";
        videos.forEach((v, index) => {
            const isMp4 = v.codec.includes('avc') || v.ext === 'mp4';
            const badgeClass = isMp4 ? 'badge-mp4' : 'badge-webm';
            const badgeText = isMp4 ? 'MP4 (H.264)' : 'WebM (VP9)';
            const html = `<label class="radio-label"><input type="radio" name="video_id" value="${v.id}" ${index===0 ? 'checked' : ''}><div><span class="info-main">${v.res}</span> <span class="badge ${badgeClass}">${badgeText}</span></div><div class="info-sub">${v.filesize} • ${v.fps}fps</div></label>`;
            vList.insertAdjacentHTML('beforeend', html);
        });
        audios.forEach((a, index) => {
            const html = `<label class="radio-label"><input type="radio" name="audio_id" value="${a.id}" ${index===0 ? 'checked' : ''}><div><span class="info-main">${a.ext.toUpperCase()}</span><span class="badge" style="background:#555">${a.codec}</span></div><div class="info-sub">${a.filesize} • ${a.abr}kbps</div></label>`;
            aList.insertAdjacentHTML('beforeend', html);
        });
    }

    async function startDownload() {
        const videoId = document.querySelector('input[name="video_id"]:checked').value;
        const audioId = document.querySelector('input[name="audio_id"]:checked').value;
        document.getElementById('btnDownload').disabled = true;
        document.getElementById('progressArea').style.display = 'block';
        
        const formData = new FormData();
        formData.append('url', currentUrl);
        formData.append('video_id', videoId);
        formData.append('audio_id', audioId);

        const response = await fetch('/download_custom', { method: 'POST', body: formData });
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        const progressBar = document.getElementById('progressBar');
        const statusText = document.getElementById('statusText');

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
                        statusText.innerText = `Đang tải: ${data.percent}% | Tốc độ: ${data.speed}`;
                    } else if (data.status === 'merging') {
                        progressBar.style.width = '99%';
                        progressBar.style.backgroundColor = '#ffc107';
                        statusText.innerText = 'Đang ghép (Muxing) vào MP4...';
                    } else if (data.status === 'finished') {
                        progressBar.style.width = '100%';
                        statusText.innerText = 'Hoàn tất!';
                        document.getElementById('finalLink').href = '/get_file/' + encodeURIComponent(data.filename);
                        document.getElementById('finalLinkArea').style.display = 'block';
                    } else if (data.status === 'error') {
                        statusText.innerText = 'Lỗi: ' + data.message;
                        statusText.style.color = 'red';
                    }
                } catch(e) {}
            }
        }
    }
</script>

</body>
</html>
"""

@app.route('/', methods=['GET'])
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/analyze', methods=['POST'])
def analyze():
    url = request.form.get('url')
    ydl_opts = {
        'cookiefile': 'cookies.txt',
        'quiet': True,
        'skip_download': True,
        'ffmpeg_location': '/usr/bin/ffmpeg', 
        # Sử dụng Web Client (đã có NodeJS để giải mã)
        'extractor_args': {'youtube': {'player_client': ['web']}},
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])

        video_opts = []
        audio_opts = []

        for f in formats:
            if f.get('vcodec') != 'none' and f.get('acodec') == 'none':
                filesize = f.get('filesize') or f.get('filesize_approx') or 0
                video_opts.append({
                    'id': f['format_id'],
                    'res': f.get('format_note') or f"{f.get('height')}p",
                    'ext': f['ext'],
                    'codec': f['vcodec'],
                    'fps': f.get('fps', 30),
                    'filesize': f"{round(filesize / 1024 / 1024, 1)} MB" if filesize else "N/A"
                })
            elif f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                filesize = f.get('filesize') or f.get('filesize_approx') or 0
                audio_opts.append({
                    'id': f['format_id'],
                    'ext': f['ext'],
                    'codec': f['acodec'],
                    'abr': int(f.get('abr') or 0),
                    'filesize': f"{round(filesize / 1024 / 1024, 1)} MB" if filesize else "N/A"
                })
        video_opts.reverse(); audio_opts.reverse()
        return jsonify({'videos': video_opts, 'audios': audio_opts})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/download_custom', methods=['POST'])
def download_custom():
    url = request.form.get('url')
    vid_id = request.form.get('video_id')
    aud_id = request.form.get('audio_id')

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
            'cookiefile': 'cookies.txt',
            'ffmpeg_location': '/usr/bin/ffmpeg',
            'quiet': True,
            'progress_hooks': [progress_hook],
            'extractor_args': {'youtube': {'player_client': ['web']}},
            'format': f"{vid_id}+{aud_id}",
            'merge_output_format': 'mp4' 
        }

        try:
            with YoutubeDL(ydl_opts) as ydl:
                ydl.extract_info(url, download=True)
            files = [f for f in glob.glob('/tmp/*') if not f.endswith('.txt') and not f.endswith('.part')]
            if files:
                final_file = max(files, key=os.path.getctime)
                yield json.dumps({'status': 'finished', 'filename': os.path.basename(final_file)}) + "\n"
            else:
                yield json.dumps({'status': 'error', 'message': 'Không thấy file'}) + "\n"
        except Exception as e:
            yield json.dumps({'status': 'error', 'message': str(e)}) + "\n"

    return Response(stream_with_context(generate()), mimetype='text/plain')

@app.route('/get_file/<filename>')
def get_file(filename):
    safe_path = os.path.join('/tmp', filename)
    if os.path.exists(safe_path):
        return send_file(safe_path, as_attachment=True)
    return "Not Found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
