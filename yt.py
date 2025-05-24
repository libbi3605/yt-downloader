from flask import Flask, render_template_string, request, jsonify, send_file, after_this_request
import yt_dlp
import os
import tempfile
import threading
import time
import uuid
from datetime import datetime, timedelta

app = Flask(__name__)

# Store download progress
download_progress = {}
download_files = {}

# Clean up old files periodically
def cleanup_old_files():
    while True:
        time.sleep(300)  # Check every 5 minutes
        current_time = datetime.now()
        to_remove = []
        
        for file_id, file_info in download_files.items():
            if current_time - file_info['created'] > timedelta(hours=1):
                try:
                    if os.path.exists(file_info['path']):
                        os.remove(file_info['path'])
                    to_remove.append(file_id)
                except:
                    pass
        
        for file_id in to_remove:
            download_files.pop(file_id, None)
            download_progress.pop(file_id, None)

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube Downloader</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        
        .container {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            padding: 40px;
            max-width: 600px;
            width: 100%;
        }
        
        .logo {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .logo h1 {
            color: #333;
            font-size: 2.5em;
            font-weight: 300;
            margin-bottom: 10px;
        }
        
        .logo p {
            color: #666;
            font-size: 1.1em;
        }
        
        .form-group {
            margin-bottom: 25px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 500;
        }
        
        input[type="url"] {
            width: 100%;
            padding: 15px;
            border: 2px solid #e1e5e9;
            border-radius: 12px;
            font-size: 16px;
            transition: all 0.3s ease;
            background: #f8f9fa;
        }
        
        input[type="url"]:focus {
            outline: none;
            border-color: #667eea;
            background: white;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .options-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 25px;
        }
        
        select {
            width: 100%;
            padding: 12px;
            border: 2px solid #e1e5e9;
            border-radius: 12px;
            font-size: 14px;
            background: #f8f9fa;
            transition: all 0.3s ease;
        }
        
        select:focus {
            outline: none;
            border-color: #667eea;
            background: white;
        }
        
        .download-btn {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-bottom: 20px;
        }
        
        .download-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(102, 126, 234, 0.3);
        }
        
        .download-btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        
        .progress-container {
            display: none;
            margin: 20px 0;
        }
        
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e1e5e9;
            border-radius: 4px;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            width: 0%;
            transition: width 0.3s ease;
        }
        
        .progress-text {
            text-align: center;
            margin-top: 10px;
            color: #666;
            font-size: 14px;
        }
        
        .result {
            margin-top: 20px;
            padding: 15px;
            border-radius: 12px;
            display: none;
        }
        
        .result.success {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
        }
        
        .result.error {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
        }
        
        .download-link {
            display: inline-block;
            margin-top: 10px;
            padding: 10px 20px;
            background: #28a745;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 500;
            transition: all 0.3s ease;
        }
        
        .download-link:hover {
            background: #218838;
            transform: translateY(-1px);
        }
        
        @media (max-width: 600px) {
            .container {
                padding: 30px 20px;
            }
            
            .options-grid {
                grid-template-columns: 1fr;
            }
            
            .logo h1 {
                font-size: 2em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <h1>📺 YouTube Downloader</h1>
            <p>Download videos and audio in high quality</p>
        </div>
        
        <form id="downloadForm">
            <div class="form-group">
                <label for="url">YouTube URL</label>
                <input type="url" id="url" name="url" placeholder="https://www.youtube.com/watch?v=..." required>
            </div>
            
            <div class="options-grid">
                <div class="form-group">
                    <label for="format">Format</label>
                    <select id="format" name="format">
                        <option value="mp4">Video (MP4)</option>
                        <option value="webm">Video (WebM)</option>
                        <option value="mp3">Audio (MP3)</option>
                        <option value="m4a">Audio (M4A)</option>
                        <option value="wav">Audio (WAV)</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="quality">Quality</label>
                    <select id="quality" name="quality">
                        <option value="best">Best Available</option>
                        <option value="1080">1080p</option>
                        <option value="720">720p</option>
                        <option value="480">480p</option>
                        <option value="360">360p</option>
                    </select>
                </div>
            </div>
            
            <button type="submit" class="download-btn" id="downloadBtn">
                🚀 Start Download
            </button>
        </form>
        
        <div class="progress-container" id="progressContainer">
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill"></div>
            </div>
            <div class="progress-text" id="progressText">Preparing download...</div>
        </div>
        
        <div class="result" id="result"></div>
    </div>

    <script>
        const form = document.getElementById('downloadForm');
        const downloadBtn = document.getElementById('downloadBtn');
        const progressContainer = document.getElementById('progressContainer');
        const progressFill = document.getElementById('progressFill');
        const progressText = document.getElementById('progressText');
        const result = document.getElementById('result');

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(form);
            const data = Object.fromEntries(formData);
            
            // Reset UI
            downloadBtn.disabled = true;
            downloadBtn.textContent = '⏳ Processing...';
            progressContainer.style.display = 'block';
            result.style.display = 'none';
            progressFill.style.width = '0%';
            progressText.textContent = 'Starting download...';
            
            try {
                const response = await fetch('/download', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data)
                });
                
                const responseData = await response.json();
                
                if (responseData.success) {
                    const downloadId = responseData.download_id;
                    
                    // Poll for progress
                    const pollProgress = setInterval(async () => {
                        try {
                            const progressResponse = await fetch(`/progress/${downloadId}`);
                            const progressData = await progressResponse.json();
                            
                            if (progressData.progress !== undefined) {
                                progressFill.style.width = progressData.progress + '%';
                                progressText.textContent = progressData.status;
                            }
                            
                            if (progressData.completed) {
                                clearInterval(pollProgress);
                                
                                if (progressData.success) {
                                    result.className = 'result success';
                                    result.innerHTML = `
                                        <strong>✅ Download Complete!</strong>
                                        <br>
                                        <a href="/file/${downloadId}" class="download-link" download>
                                            📥 Download File
                                        </a>
                                    `;
                                    progressText.textContent = 'Download ready!';
                                    progressFill.style.width = '100%';
                                } else {
                                    result.className = 'result error';
                                    result.innerHTML = `<strong>❌ Error:</strong> ${progressData.error}`;
                                }
                                
                                result.style.display = 'block';
                                downloadBtn.disabled = false;
                                downloadBtn.textContent = '🚀 Start Download';
                                progressContainer.style.display = 'none';
                            }
                        } catch (error) {
                            console.error('Progress polling error:', error);
                        }
                    }, 1000);
                    
                } else {
                    throw new Error(responseData.error);
                }
                
            } catch (error) {
                result.className = 'result error';
                result.innerHTML = `<strong>❌ Error:</strong> ${error.message}`;
                result.style.display = 'block';
                
                downloadBtn.disabled = false;
                downloadBtn.textContent = '🚀 Start Download';
                progressContainer.style.display = 'none';
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/download', methods=['POST'])
def download():
    try:
        data = request.get_json()
        url = data.get('url')
        format_type = data.get('format', 'mp4')
        quality = data.get('quality', 'best')
        
        if not url:
            return jsonify({'success': False, 'error': 'URL is required'})
        
        # Generate unique download ID
        download_id = str(uuid.uuid4())
        
        # Initialize progress
        download_progress[download_id] = {
            'progress': 0,
            'status': 'Starting download...',
            'completed': False,
            'success': False,
            'error': None
        }
        
        # Start download in background
        thread = threading.Thread(
            target=process_download,
            args=(download_id, url, format_type, quality)
        )
        thread.start()
        
        return jsonify({'success': True, 'download_id': download_id})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

def progress_hook(d):
    download_id = d.get('download_id')
    if not download_id:
        return
        
    if d['status'] == 'downloading':
        if 'total_bytes' in d and d['total_bytes']:
            progress = (d['downloaded_bytes'] / d['total_bytes']) * 100
        elif '_percent_str' in d:
            progress = float(d['_percent_str'].replace('%', ''))
        else:
            progress = 0
            
        download_progress[download_id].update({
            'progress': min(progress, 99),
            'status': f'Downloading... {progress:.1f}%'
        })
    elif d['status'] == 'finished':
        download_progress[download_id].update({
            'progress': 100,
            'status': 'Processing...'
        })

def process_download(download_id, url, format_type, quality):
    try:
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Configure yt-dlp options
        is_audio = format_type in ['mp3', 'm4a', 'wav']
        
        ydl_opts = {
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [lambda d: {**d, 'download_id': download_id} and progress_hook({**d, 'download_id': download_id})]
        }
        
        if is_audio:
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': format_type,
                    'preferredquality': '192' if format_type == 'mp3' else None,
                }]
            })
        else:
            if quality == 'best':
                ydl_opts['format'] = f'best[ext={format_type}]/best'
            else:
                ydl_opts['format'] = f'best[height<={quality}][ext={format_type}]/best[height<={quality}]'
        
        download_progress[download_id]['status'] = 'Fetching video info...'
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get video info
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'video')
            
            download_progress[download_id]['status'] = f'Downloading: {title[:50]}...'
            
            # Download
            ydl.download([url])
        
        # Find the downloaded file
        files = os.listdir(temp_dir)
        if not files:
            raise Exception("No file was downloaded")
        
        downloaded_file = os.path.join(temp_dir, files[0])
        
        # Store file info
        download_files[download_id] = {
            'path': downloaded_file,
            'filename': files[0],
            'created': datetime.now()
        }
        
        download_progress[download_id].update({
            'progress': 100,
            'status': 'Download complete!',
            'completed': True,
            'success': True
        })
        
    except Exception as e:
        download_progress[download_id].update({
            'completed': True,
            'success': False,
            'error': str(e)
        })

@app.route('/progress/<download_id>')
def get_progress(download_id):
    progress = download_progress.get(download_id, {
        'progress': 0,
        'status': 'Unknown',
        'completed': True,
        'success': False,
        'error': 'Download not found'
    })
    return jsonify(progress)

@app.route('/file/<download_id>')
def download_file(download_id):
    file_info = download_files.get(download_id)
    if not file_info or not os.path.exists(file_info['path']):
        return "File not found", 404
    
    @after_this_request
    def remove_file(response):
        try:
            # Schedule file removal after a delay
            def delayed_remove():
                time.sleep(5)
                try:
                    if os.path.exists(file_info['path']):
                        os.remove(file_info['path'])
                    download_files.pop(download_id, None)
                    download_progress.pop(download_id, None)
                except:
                    pass
            
            threading.Thread(target=delayed_remove, daemon=True).start()
        except:
            pass
        return response
    
    return send_file(
        file_info['path'],
        as_attachment=True,
        download_name=file_info['filename']
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)