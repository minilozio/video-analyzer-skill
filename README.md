# Video Analyzer Skill 🎥

A powerful OpenClaw skill to download, transcribe, and analyze videos from YouTube, X/Twitter, TikTok, and more. 

It uses a smart two-tier architecture to get you the results as fast as possible, while keeping everything **100% free and private** by running models locally on your machine.

---

## ⚡ How it Works (Two-Tier Architecture)

1. **Level 1 (Fast Track):** If the video is on YouTube and has captions (manual or auto-generated), the skill uses `yt-dlp` to extract the subtitle text instantly. **Time to transcript: ~3 seconds.**
2. **Level 2 (Deep Fallback):** If it's a video on X/Twitter, TikTok, or a YouTube video without captions, the skill downloads the audio track and transcribes it locally using `whisper-cpp`. **Time to transcript: ~20 seconds** (for a 20-minute video on an M-series Mac).

Zero API keys needed. Zero cloud costs. 

## 🛠️ Features

- **Download:** Save any video as MP4 or extract the audio as MP3/M4A.
- **Transcribe:** Get accurate, timestamped transcripts of any video.
- **Analyze:** The agent automatically processes the transcript to give you a structured summary:
  - 📝 **TL;DR**
  - ⏱️ **Key Moments** (with timestamps)
  - 💡 **Actionable Insights**
- **Search:** Ask your agent "At what minute does he talk about X?" and it will pinpoint the exact timestamp.

## 🚀 Installation

```bash
clawhub install video-analyzer
```

**Dependencies:**
This skill relies on standard open-source tools. OpenClaw will attempt to install them automatically via Homebrew:
- `yt-dlp` (Universal media downloader)
- `ffmpeg` (Audio processing)
- `whisper-cpp` (Local transcription engine)

## 🎛️ Quality Presets for Local Transcription

If the skill falls back to local Whisper transcription, it uses the `base.en` model by default (fast and accurate for English). You can ask your agent to use different quality presets based on your hardware:

- **Fast:** `--quality fast` (tiny model, ~75MB RAM)
- **Normal:** `--quality normal` (base model, ~150MB RAM) - *Default*
- **High:** `--quality high` (medium model, ~1.5GB RAM)
- **Max:** `--quality max` (large-v3-turbo, ~3GB RAM, studio quality)

*Models are automatically downloaded to `/opt/homebrew/share/whisper-cpp/` on first use.*

## 🗣️ Example Prompts

- *"Give me a summary and the key moments of this YouTube video: [link]"*
- *"Extract the audio from this X post and save it to my desktop: [link]"*
- *"Transcribe this TikTok using max quality settings: [link]"*
- *"In what minute of this podcast do they mention Solana? [link]"*

---
*Built with 🦎 by the creators of [Agent Arena](https://agentarena.chat) — The first social network where AI agents have real conversations.*