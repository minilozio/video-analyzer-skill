#!/usr/bin/env python3
import argparse
import subprocess
import os
import sys
import hashlib
import re
import urllib.request
import shutil
from pathlib import Path

# --- Configuration ---
MODELS_DIR = Path("/opt/homebrew/share/whisper-cpp")
WHISPER_MODELS = {
    "fast": "ggml-tiny.bin",
    "normal": "ggml-base.en.bin",
    "high": "ggml-medium.bin",
    "max": "ggml-large-v3-turbo.bin"
}
WHISPER_BASE_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/"

def run_cmd(cmd, check=True):
    """Run a shell command and return stdout."""
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        if check:
            print(f"Error running: {cmd}", file=sys.stderr)
            print(e.stderr, file=sys.stderr)
            sys.exit(1)
        return ""

def download_model_if_needed(model_filename):
    """Download whisper model to Homebrew share dir if missing."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODELS_DIR / model_filename
    
    if not model_path.exists():
        print(f"Downloading Whisper model '{model_filename}' (this only happens once)...", file=sys.stderr)
        url = WHISPER_BASE_URL + model_filename
        try:
            # Using curl for progress bar in stderr
            run_cmd(f'curl -L "{url}" -o "{model_path}"')
        except Exception as e:
            print(f"Failed to download model: {e}", file=sys.stderr)
            sys.exit(1)
    return str(model_path)

def clean_vtt(vtt_path, txt_path):
    """Convert VTT subtitle file to clean timestamped text."""
    with open(vtt_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    cleaned = []
    current_time = ""
    last_text = ""
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('WEBVTT') or '-->' not in line and not line.strip():
            continue
            
        # Extract time: 00:01:23.450 --> 00:01:25.000
        if '-->' in line:
            # Keep just MM:SS or HH:MM:SS of the start time
            time_match = re.search(r'(\d{2}:\d{2}(?::\d{2})?)', line)
            if time_match:
                current_time = time_match.group(1)
            continue
            
        # Clean text (remove html-like tags like <c> etc)
        text = re.sub(r'<[^>]+>', '', line).strip()
        # Skip duplicate lines (youtube auto-subs duplicate a lot)
        if text and text != last_text and not text.isdigit():
            cleaned.append(f"[{current_time}] {text}")
            last_text = text

    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(cleaned))

def handle_transcript(url, quality, lang):
    """Two-tier transcript extraction."""
    # Create temp dir based on URL hash
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    tmp_dir = Path(f"/tmp/video_analyzer_{url_hash}")
    tmp_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Analyzing: {url}", file=sys.stderr)
    
    # ---------------------------------------------------------
    # LEVEL 1: Fast Track (yt-dlp auto-subs)
    # ---------------------------------------------------------
    print("Level 1: Attempting to extract native subtitles...", file=sys.stderr)
    subs_out = tmp_dir / "subs"
    cmd_subs = f"yt-dlp --write-auto-subs --write-subs --sub-langs '{lang}.*' --skip-download -o '{subs_out}' '{url}'"
    run_cmd(cmd_subs, check=False)
    
    # Find generated VTT
    vtt_files = list(tmp_dir.glob("*.vtt"))
    if vtt_files:
        print("Native subtitles found! Processing...", file=sys.stderr)
        vtt_file = vtt_files[0]
        txt_file = tmp_dir / "transcript.txt"
        clean_vtt(vtt_file, txt_file)
        print(f"SUCCESS: Transcript saved to:\n{txt_file}")
        return

    # ---------------------------------------------------------
    # LEVEL 2: Deep Fallback (Whisper local)
    # ---------------------------------------------------------
    print("Level 1 failed (No subs found or unsupported platform).", file=sys.stderr)
    print("Level 2: Falling back to local Whisper transcription...", file=sys.stderr)
    
    audio_m4a = tmp_dir / "audio.m4a"
    audio_wav = tmp_dir / "audio.wav"
    
    # 1. Download Audio
    print("Downloading audio track...", file=sys.stderr)
    run_cmd(f"yt-dlp -f 'bestaudio[ext=m4a]/bestaudio/best' -o '{audio_m4a}' '{url}'")
    
    # 2. Convert to WAV 16kHz (required by whisper-cpp)
    print("Converting to 16kHz WAV...", file=sys.stderr)
    run_cmd(f"ffmpeg -i '{audio_m4a}' -ar 16000 -ac 1 -c:a pcm_s16le '{audio_wav}' -y")
    
    # 3. Check/Download Model
    model_filename = WHISPER_MODELS.get(quality, WHISPER_MODELS["normal"])
    if lang != 'en' and '.en' in model_filename:
        model_filename = model_filename.replace('.en', '') # Fallback to multilingual
        
    model_path = download_model_if_needed(model_filename)
    
    # 4. Transcribe
    print(f"Transcribing using {model_filename}... (this may take a moment)", file=sys.stderr)
    txt_out = tmp_dir / "transcript"
    lang_flag = f"-l {lang}" if lang != 'en' else ""
    
    run_cmd(f"whisper-cli -m '{model_path}' -f '{audio_wav}' {lang_flag} --output-txt --output-file '{txt_out}'")
    
    final_txt = tmp_dir / "transcript.txt"
    if final_txt.exists():
        print(f"SUCCESS: Transcript saved to:\n{final_txt}")
    else:
        print("Transcription failed.", file=sys.stderr)
        sys.exit(1)

def handle_download(url, action):
    """Download video or audio to Desktop."""
    desktop = Path.home() / "Desktop"
    
    if action == "download-video":
        print("Downloading best video quality to Desktop...", file=sys.stderr)
        cmd = f"yt-dlp -f 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best' -o '{desktop}/%(title)s.%(ext)s' '{url}'"
    else:
        print("Downloading best audio quality to Desktop...", file=sys.stderr)
        cmd = f"yt-dlp -f 'bestaudio[ext=m4a]/bestaudio/best' -o '{desktop}/%(title)s.%(ext)s' '{url}'"
        
    out = run_cmd(cmd)
    
    # Extract destination path from yt-dlp output
    dest = ""
    for line in out.split('\n'):
        if "Destination:" in line:
            dest = line.split("Destination:")[1].strip()
        elif "has already been downloaded" in line:
            dest = line.split("[download]")[1].split("has already")[0].strip()
            
    print(f"SUCCESS: Downloaded to:\n{dest}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Video Analyzer for OpenClaw")
    parser.add_argument("--url", required=True, help="Video URL")
    parser.add_argument("--action", required=True, choices=["transcript", "download-video", "download-audio"])
    parser.add_argument("--quality", choices=["fast", "normal", "high", "max"], default="normal", help="Whisper model quality")
    parser.add_argument("--lang", default="en", help="Language code (e.g., 'en', 'it')")
    
    args = parser.parse_args()
    
    if args.action == "transcript":
        handle_transcript(args.url, args.quality, args.lang)
    else:
        handle_download(args.url, args.action)
