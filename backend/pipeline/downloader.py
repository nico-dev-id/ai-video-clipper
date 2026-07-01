import yt_dlp
import os

OUTPUT_DIR = "outputs"

def download_video(url: str) -> dict:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    ydl_opts = {
        "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
        "outtmpl": f"{OUTPUT_DIR}/%(id)s/source.%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    video_id = info["id"]
    output_dir = f"{OUTPUT_DIR}/{video_id}"
    video_path = f"{output_dir}/source.mp4"

    return {
        "video_id": video_id,
        "video_path": video_path,
        "output_dir": output_dir,
        "title": info["title"],
        "channel": info["uploader"],
        "duration": info["duration"],
    }