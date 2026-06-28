import yt_dlp
import os

OUTPUT_DIR = "outputs"

def download_video(url: str) -> dict:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    ydl_opts = {
        "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
        "outtmpl": f"{OUTPUT_DIR}/%(id)s.%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    video_id = info["id"]
    video_path = f"{OUTPUT_DIR}/{video_id}.mp4"

    return {
        "video_id": video_id,
        "video_path": video_path,
        "title": info["title"],
        "channel": info["uploader"],
        "duration": info["duration"],
    }