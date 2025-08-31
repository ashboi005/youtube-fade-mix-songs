# YouTube Mixtape Maker

Create custom mixtapes from YouTube videos with seamless overlapping fades.

## Features

- **Smart Download**: cnvmp3.com primary, YTMP3 fallback
- **Overlapping Fades**: Songs blend together with crossfades
- **Custom Segments**: Choose start/end times for each song
- **Web Interface**: Simple Flask web app

## Requirements

- Python 3.7+
- FFMPEG
- Chrome browser

## Setup

1. **Install dependencies:**
```bash
pip install flask selenium webdriver-manager
```

2. **Install FFMPEG:**
   - Windows: Download from https://ffmpeg.org/
   - Mac: `brew install ffmpeg`
   - Linux: `sudo apt install ffmpeg`

3. **Run app:**
```bash
python app_clean.py
```

4. **Open browser:** http://localhost:5000

## Usage

1. Enter YouTube URLs
2. Set start/end times for each song
3. Configure fade in/out durations
4. Click "Create Mixtape"
5. Download your custom mixtape

## File Structure

```
mixtape-maker/
├── app_clean.py          # Main application
├── requirements.txt      # Dependencies
├── templates/           # HTML templates
│   ├── base.html
│   ├── index.html
│   └── success.html
└── temp/               # Temporary files (auto-created)
```

## How It Works

1. **Download**: Uses cnvmp3.com (tries 2x) then YTMP3 fallback
2. **Extract**: FFMPEG extracts specified segments from downloaded audio
3. **Crossfade**: Creates overlapping transitions between songs (3s default)
4. **Output**: Single MP3 file with seamless transitions

## Notes

- Downloads are temporary and cleaned up automatically
- Overlapping fades create smooth DJ-style transitions
- Handles various audio formats (MP3, M4A, etc.)
- Runs headless for better performance
