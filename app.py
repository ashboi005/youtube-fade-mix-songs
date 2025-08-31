from flask import Flask, request, jsonify, send_file, render_template, redirect, url_for, flash
import tempfile
import uuid
import shutil
from pathlib import Path
import logging

from utils import (
    validate_youtube_url,
    check_tools,
    download_youtube_audio,
    extract_segment,
    apply_fades,
    get_audio_duration,
    concatenate_audio,
    create_overlapping_mixtape
)

app = Flask(__name__)
app.secret_key = 'mixtape-generator-secret-key'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TEMP_DIR = Path("temp")
TEMP_DIR.mkdir(exist_ok=True)

@app.route('/')
def index():
    """Main page - shows the mixtape creation form"""
    tools = check_tools()
    return render_template('index.html', tools=tools)

@app.route('/create', methods=['POST'])
def create_mixtape():
    """Process the mixtape creation request"""
    try:
        # Parse songs from form data
        songs = []
        i = 0
        while f'youtube_url_{i}' in request.form:
            youtube_url = request.form.get(f'youtube_url_{i}', '').strip()
            if youtube_url:
                songs.append({
                    'youtubeUrl': youtube_url,
                    'startTime': float(request.form.get(f'start_time_{i}', 0)),
                    'endTime': float(request.form.get(f'end_time_{i}', 30)),
                    'fadeIn': float(request.form.get(f'fade_in_{i}', 2)),
                    'fadeOut': float(request.form.get(f'fade_out_{i}', 2))
                })
            i += 1
        
        # Validate input
        if not songs:
            flash('Please add at least one song with a YouTube URL', 'error')
            return redirect(url_for('index'))
        
        for i, song in enumerate(songs):
            if not validate_youtube_url(song['youtubeUrl']):
                flash(f'Invalid YouTube URL for song {i+1}', 'error')
                return redirect(url_for('index'))
            
            if song['endTime'] <= song['startTime']:
                flash(f'End time must be greater than start time for song {i+1}', 'error')
                return redirect(url_for('index'))
        
        # Create session directory
        session_id = uuid.uuid4().hex
        session_dir = TEMP_DIR / session_id
        session_dir.mkdir(exist_ok=True)
        
        processed_files = []
        fade_info = []
        
        try:
            # Process each song
            for i, song in enumerate(songs):
                # Download audio
                download_path = session_dir / f"download_{i}"
                downloaded_file = download_youtube_audio(song['youtubeUrl'], download_path)
                
                if not downloaded_file.exists() or downloaded_file.stat().st_size == 0:
                    raise Exception(f"Download failed for song {i+1}")
                
                # Extract segment
                start_time = max(0, song['startTime'])
                end_time = song['endTime']
                segment_duration = end_time - start_time
                
                segment_file = session_dir / f"segment_{i}.mp3"
                extract_segment(downloaded_file, segment_file, start_time, segment_duration)
                
                if not segment_file.exists():
                    raise Exception(f"Segment extraction failed for song {i+1}")
                
                processed_files.append(segment_file)
                fade_info.append({
                    'fadeIn': song['fadeIn'],
                    'fadeOut': song['fadeOut']
                })
                
                # Clean up downloaded file
                if downloaded_file.exists():
                    downloaded_file.unlink()
            
            # Create the final mixtape with overlapping fades
            final_mixtape = session_dir / "final_mixtape.mp3"
            
            for f in processed_files:
                if not f.exists():
                    raise Exception(f"Processed file missing: {f}")
            
            create_overlapping_mixtape(processed_files, fade_info, final_mixtape, overlap_duration=3.0)
            
            # Clean up segment files
            for f in processed_files:
                if f.exists():
                    f.unlink()
            
            flash('🎉 Your mixtape has been created successfully!', 'success')
            return redirect(url_for('download_page', session_id=session_id))
            
        except Exception as e:
            shutil.rmtree(session_dir, ignore_errors=True)
            raise e
            
    except Exception as e:
        logger.error(f"Error creating mixtape: {str(e)}")
        flash(f'Error creating mixtape: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/download/<session_id>')
def download_mixtape(session_id):
    """Download the created mixtape file"""
    try:
        session_dir = TEMP_DIR / session_id
        mixtape_file = session_dir / "final_mixtape.mp3"
        
        if not mixtape_file.exists():
            flash('Mixtape not found or expired', 'error')
            return redirect(url_for('index'))
        
        return send_file(
            mixtape_file,
            as_attachment=True,
            download_name=f'mixtape_{session_id}.mp3',
            mimetype='audio/mpeg'
        )
        
    except Exception as e:
        flash(f'Error downloading mixtape: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/success/<session_id>')
def download_page(session_id):
    """Success page showing download link"""
    session_dir = TEMP_DIR / session_id
    mixtape_file = session_dir / "final_mixtape.mp3"
    
    if not mixtape_file.exists():
        flash('Mixtape not found or expired', 'error')
        return redirect(url_for('index'))
    
    return render_template('success.html', session_id=session_id)

@app.route('/get_video_info', methods=['POST'])
def get_video_info():
    """Get YouTube video information using yt-dlp"""
    try:
        import yt_dlp
        
        data = request.get_json()
        url = data.get('url', '').strip()
        
        if not url or not validate_youtube_url(url):
            return {'success': False, 'error': 'Invalid YouTube URL'}, 400
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            title = info.get('title', 'Unknown Title')
            duration = info.get('duration', 0)
            uploader = info.get('uploader', 'Unknown')
            
            return {
                'success': True,
                'title': title,
                'duration': duration,
                'uploader': uploader,
                'duration_formatted': f"{duration // 60}:{duration % 60:02d}" if duration else "Unknown"
            }
            
    except ImportError:
        return {'success': False, 'error': 'yt-dlp not available'}, 400
    except Exception as e:
        return {'success': False, 'error': str(e)}, 400

if __name__ == '__main__':
    print("🎵 YouTube Mixtape Generator")
    print("=" * 40)
    
    tools = check_tools()
    if tools['ffmpeg']:
        print("✅ FFMPEG available")
    else:
        print("⚠️ FFMPEG missing - install from https://ffmpeg.org/")
    
    try:
        from utils import HAS_SELENIUM
        if HAS_SELENIUM:
            print("✅ Selenium available")
        else:
            print("⚠️ Selenium missing - install with: pip install selenium webdriver-manager")
    except ImportError:
        print("⚠️ Selenium missing - install with: pip install selenium webdriver-manager")
    
    print("🌐 Server: http://localhost:5000")
    print("=" * 40)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
