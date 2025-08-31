"""
Utility functions for YouTube Mixtape Generator
Contains all the core functionality for downloading, processing, and mixing audio
"""

import subprocess
import tempfile
import uuid
import time
import shutil
from pathlib import Path
import logging

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False

logger = logging.getLogger(__name__)

def validate_youtube_url(url):
    """Validate if the URL is a valid YouTube URL"""
    import re
    youtube_regex = r'^(https?://)?(www\.)?(youtube\.com/(watch\?v=|embed/)|youtu\.be/)[\w\-]+'
    return re.match(youtube_regex, url) is not None

def check_tools():
    """Check if required tools (FFMPEG and yt-dlp) are available"""
    tools = {'ffmpeg': False, 'yt_dlp': False}
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True)
        tools['ffmpeg'] = result.returncode == 0
    except FileNotFoundError:
        pass
    
    try:
        import yt_dlp
        tools['yt_dlp'] = True
    except ImportError:
        pass
    
    return tools

def download_youtube_audio_cnvmp3(url, output_path):
    """Download YouTube audio using cnvmp3.com service"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    temp_download_dir = str(output_path.parent.absolute())
    prefs = {
        "download.default_directory": temp_download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        driver.get("https://cnvmp3.com/v33")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "video-url")))
        
        url_input = driver.find_element(By.ID, "video-url")
        url_input.clear()
        url_input.send_keys(url)
        
        try:
            mp3_option = driver.find_element(By.CSS_SELECTOR, '.format-select-options[data-format="1"].active')
        except:
            try:
                mp3_option = driver.find_element(By.CSS_SELECTOR, '.format-select-options[data-format="1"]')
                mp3_option.click()
            except:
                pass
        
        temp_dir = output_path.parent
        initial_files = set(temp_dir.glob("*"))
        
        convert_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "convert-button-1"))
        )
        convert_button.click()
        
        downloaded_file = None
        for attempt in range(90):
            time.sleep(1)
            current_files = set(temp_dir.glob("*"))
            new_files = current_files - initial_files
            
            for file_path in new_files:
                if file_path.is_file() and file_path.suffix.lower() in ['.mp3', '.m4a', '.wav', '.webm', '.mp4']:
                    filename = file_path.name.lower()
                    if not (filename.startswith('faded_') or filename.startswith('segment_') or 
                           filename.startswith('download_') or filename == 'final_mixtape.mp3' or
                           filename.endswith('.crdownload')):
                        if file_path.stat().st_size > 10240:
                            downloaded_file = file_path
                            break
            
            if downloaded_file:
                break
        
        if not downloaded_file:
            raise Exception("cnvmp3 download failed")
        
        final_output_path = output_path.with_suffix(downloaded_file.suffix)
        if downloaded_file != final_output_path:
            shutil.move(str(downloaded_file), str(final_output_path))
        
        if final_output_path.stat().st_size == 0:
            raise Exception("Downloaded file is empty")
        
        return final_output_path
        
    except Exception as e:
        raise e
    finally:
        driver.quit()

def download_youtube_audio_ytmp3(url, output_path):
    """Download YouTube audio using ytmp3.as service as fallback"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    temp_download_dir = str(output_path.parent.absolute())
    temp_dir = output_path.parent
    
    for existing_file in temp_dir.glob("*"):
        if existing_file.is_file() and existing_file.suffix.lower() in ['.mp3', '.m4a', '.wav', '.webm', '.mp4']:
            filename = existing_file.name.lower()
            if not (filename.startswith('faded_') or filename.startswith('segment_') or 
                   filename.startswith('download_') or filename == 'final_mixtape.mp3'):
                try:
                    existing_file.unlink()
                except:
                    pass
    
    prefs = {
        "download.default_directory": temp_download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        driver.get("https://ytmp3.as/AOPR/")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, "v")))
        
        url_input = driver.find_element(By.NAME, "v")
        url_input.clear()
        url_input.send_keys(url)
        
        convert_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@type='submit' or contains(text(), 'Convert')]"))
        )
        convert_button.click()
        time.sleep(6)
        
        download_button = None
        for attempt in range(8):
            try:
                download_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Download') or @type='button']")
                for btn in download_buttons:
                    text = btn.text.strip().lower()
                    if "download" in text and "next" not in text:
                        download_button = btn
                        break
                
                if download_button:
                    download_button.click()
                    time.sleep(3)
                    break
                time.sleep(5)
            except Exception:
                time.sleep(5)
        
        if not download_button:
            try:
                driver.quit()
            except:
                pass
            downloaded_file = download_youtube_audio_cnvmp3(url, output_path)
            return downloaded_file
        
        downloaded_file = None
        for attempt in range(60):
            time.sleep(1)
            current_files = list(temp_dir.glob("*"))
            
            for file_path in current_files:
                if file_path.is_file() and file_path.suffix.lower() in ['.mp3', '.m4a', '.wav', '.webm', '.mp4']:
                    filename = file_path.name.lower()
                    if not (filename.startswith('faded_') or filename.startswith('segment_') or 
                           filename.startswith('download_') or filename == 'final_mixtape.mp3' or
                           filename.endswith('.crdownload')):
                        
                        if file_path.stat().st_size > 10240:
                            downloaded_file = file_path
                            break
            
            if downloaded_file:
                break
        
        if not downloaded_file:
            raise Exception("YTMP3 download failed")
        
        final_output_path = output_path.with_suffix(downloaded_file.suffix)
        if downloaded_file != final_output_path:
            shutil.move(str(downloaded_file), str(final_output_path))
        
        return final_output_path
        
    except Exception as e:
        raise e
    finally:
        driver.quit()

def download_youtube_audio(url, output_path):
    """Main download function with cnvmp3 primary and YTMP3 fallback"""
    if not HAS_SELENIUM:
        raise Exception("Selenium not available. Install with: pip install selenium webdriver-manager")
    
    print(f"🎵 Downloading: {url}")
    
    # Try cnvmp3.com (primary service) with 2 attempts
    for attempt in range(2):
        try:
            if attempt > 0:
                print(f"🔄 cnvmp3 retry attempt {attempt + 1}/2...")
            else:
                print("🔄 Trying cnvmp3.com (primary)...")
            
            downloaded_file = download_youtube_audio_cnvmp3(url, output_path)
            print(f"✅ cnvmp3.com successful on attempt {attempt + 1}!")
            return downloaded_file
            
        except Exception as cnv_error:
            print(f"❌ cnvmp3 attempt {attempt + 1}/2 failed: {cnv_error}")
            if attempt == 1:
                print("🔄 cnvmp3 failed, trying YTMP3 fallback...")
                break
    
    # Fallback to YTMP3
    try:
        downloaded_file = download_youtube_audio_ytmp3(url, output_path)
        print("✅ YTMP3 fallback successful!")
        return downloaded_file
    except Exception as ytmp3_error:
        print(f"❌ YTMP3 fallback failed: {ytmp3_error}")
        raise Exception(f"All services failed. cnvmp3: failed after 2 attempts, YTMP3: {ytmp3_error}")

def extract_segment(input_file, output_file, start_time, duration):
    """Extract a specific time segment from an audio file using FFMPEG"""
    if not input_file.exists():
        raise Exception(f"Input file does not exist: {input_file}")
    
    if input_file.stat().st_size == 0:
        raise Exception(f"Input file is empty: {input_file}")
    
    cmd = [
        'ffmpeg', '-i', str(input_file),
        '-ss', str(start_time),
        '-t', str(duration),
        '-acodec', 'libmp3lame',
        '-b:a', '192k',
        '-y',
        str(output_file)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"FFMPEG segment extraction failed: {result.stderr}")
    
    if not output_file.exists() or output_file.stat().st_size == 0:
        raise Exception(f"Output file creation failed: {output_file}")
    
    return output_file

def apply_fades(input_file, output_file, fade_in, fade_out, total_duration):
    """Apply fade in and fade out effects to an audio file"""
    fade_out_start = max(0, total_duration - fade_out)
    
    filters = []
    if fade_in > 0:
        filters.append(f"afade=t=in:d={fade_in}")
    if fade_out > 0:
        filters.append(f"afade=t=out:st={fade_out_start}:d={fade_out}")
    
    cmd = ['ffmpeg', '-i', str(input_file)]
    
    if filters:
        cmd.extend(['-af', ','.join(filters)])
    
    cmd.extend([
        '-acodec', 'libmp3lame',
        '-b:a', '192k',
        '-y',
        str(output_file)
    ])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"FFMPEG fade failed: {result.stderr}")
    
    return output_file

def get_audio_duration(audio_file):
    """Get the duration of an audio file in seconds"""
    cmd = [
        'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
        '-of', 'csv=p=0', str(audio_file)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Failed to get audio duration: {result.stderr}")
    
    try:
        return float(result.stdout.strip())
    except ValueError:
        raise Exception(f"Invalid duration format: {result.stdout.strip()}")

def concatenate_audio(input_files, output_file):
    """Concatenate multiple audio files into one using FFMPEG"""
    concat_file = output_file.parent / f"concat_{uuid.uuid4().hex}.txt"
    
    with open(concat_file, 'w') as f:
        for file_path in input_files:
            f.write(f"file '{file_path.absolute()}'\n")
    
    cmd = [
        'ffmpeg', '-f', 'concat', '-safe', '0',
        '-i', str(concat_file),
        '-c', 'copy',
        '-y',
        str(output_file)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    concat_file.unlink()
    
    if result.returncode != 0:
        raise Exception(f"FFMPEG concat failed: {result.stderr}")
    
    return output_file

def create_overlapping_mixtape(segment_files, fade_durations, output_file, overlap_duration=3.0):
    """Create a mixtape with overlapping crossfades between segments"""
    if len(segment_files) == 1:
        song_info = fade_durations[0]
        segment_duration = get_audio_duration(segment_files[0])
        apply_fades(segment_files[0], output_file, song_info['fadeIn'], song_info['fadeOut'], segment_duration)
        return output_file
    
    cmd = ['ffmpeg']
    
    # Add all input files
    for segment_file in segment_files:
        cmd.extend(['-i', str(segment_file)])
    
    filter_complex = []
    current_output = '[0:a]'
    
    # Process each segment with fades and overlapping
    for i in range(len(segment_files)):
        song_info = fade_durations[i]
        fade_in = song_info['fadeIn']
        fade_out = song_info['fadeOut']
        
        segment_duration = get_audio_duration(segment_files[i])
        fade_out_start = max(0, segment_duration - fade_out)
        
        # Apply fades to this segment
        fade_filters = []
        if fade_in > 0:
            fade_filters.append(f"afade=t=in:d={fade_in}")
        if fade_out > 0:
            fade_filters.append(f"afade=t=out:st={fade_out_start}:d={fade_out}")
        
        if fade_filters:
            filter_complex.append(f"[{i}:a]{','.join(fade_filters)}[faded{i}]")
            track_ref = f'[faded{i}]'
        else:
            track_ref = f'[{i}:a]'
        
        if i == 0:
            current_output = track_ref
        else:
            # Calculate delay for overlapping effect
            total_previous_duration = 0
            for j in range(i):
                prev_duration = get_audio_duration(segment_files[j])
                total_previous_duration += prev_duration
            
            delay_time = max(0, total_previous_duration - (overlap_duration * i))
            
            # Add delay and mix with previous output
            filter_complex.append(f"{track_ref}adelay={int(delay_time * 1000)}|{int(delay_time * 1000)}[delayed{i}]")
            filter_complex.append(f"{current_output}[delayed{i}]amix=inputs=2:duration=longest[mixed{i}]")
            current_output = f'[mixed{i}]'
    
    # Final resampling
    filter_complex.append(f"{current_output}aresample=44100[out]")
    
    cmd.extend(['-filter_complex', ';'.join(filter_complex)])
    cmd.extend(['-map', '[out]'])
    cmd.extend(['-acodec', 'libmp3lame', '-b:a', '192k', '-y', str(output_file)])
    
    print(f"🎵 Creating overlapping mixtape with {overlap_duration}s crossfades...")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ FFMPEG overlapping failed: {result.stderr}")
        print("🔄 Falling back to simple concatenation...")
        return concatenate_audio(segment_files, output_file)
    
    return output_file
