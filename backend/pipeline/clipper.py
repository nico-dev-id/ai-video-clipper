from moviepy import VideoFileClip, ImageClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os

OUTPUT_CLIPS_DIR = "outputs/clips"
FONT_PATH = "C:/Windows/Fonts/arialbd.ttf"


def fix_overlapping_clips(clips: list[dict], video_duration: int) -> list[dict]:
    fixed = []
    used_ranges = []
    for clip in clips:
        start = clip["start"]
        end = clip["end"]
        overlap = False
        for (s, e) in used_ranges:
            if not (end <= s or start >= e):
                overlap = True
                break
        if not overlap and end <= video_duration:
            fixed.append(clip)
            used_ranges.append((start, end))
    return fixed


def make_text_image(text: str, font_size: int, width: int, color: tuple, stroke: int = 3) -> np.ndarray:
    """Render teks ke numpy array RGBA menggunakan Pillow."""
    font = ImageFont.truetype(FONT_PATH, font_size)

    # Ukur tinggi teks
    dummy = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy)
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    # Buat canvas dengan padding
    pad = stroke + 10
    img_w = max(width, text_w + pad * 2)
    img_h = text_h + pad * 2

    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    x = (img_w - text_w) // 2
    y = pad

    # Stroke (outline)
    draw.text((x, y), text, font=font, fill=(0, 0, 0, 255), stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
    # Teks utama
    draw.text((x, y), text, font=font, fill=color + (255,))

    return np.array(img)


def build_word_chunks(segments: list[dict], start: float, end: float) -> list[dict]:
    relevant = [s for s in segments if s["end"] > start and s["start"] < end]
    words = []
    for seg in relevant:
        seg_words = seg["text"].split()
        if not seg_words:
            continue
        seg_duration = seg["end"] - seg["start"]
        word_duration = seg_duration / len(seg_words)
        for i, word in enumerate(seg_words):
            word_start = seg["start"] + (i * word_duration)
            word_end = word_start + word_duration
            words.append({"word": word, "start": word_start, "end": word_end})

    chunks = []
    for i in range(0, len(words), 3):
        chunk_words = words[i:i+3]
        if not chunk_words:
            continue
        chunks.append({
            "text": " ".join(w["word"] for w in chunk_words),
            "start": max(0, chunk_words[0]["start"] - start),
            "end": min(60, chunk_words[-1]["end"] - start),
        })
    return chunks


def create_clip(
    video_path: str,
    clip_info: dict,
    segments: list[dict],
    source_title: str,
    source_channel: str,
    clip_index: int,
) -> str:
    os.makedirs(OUTPUT_CLIPS_DIR, exist_ok=True)

    start = clip_info["start"]
    end = clip_info["end"]

    # Load dan potong video
    video = VideoFileClip(video_path).subclipped(start, end)

    # --- CONVERT KE VERTICAL 1080x1920 ---
    target_w, target_h = 1080, 1920
    orig_w, orig_h = video.size
    scale = max(target_w / orig_w, target_h / orig_h)
    new_w = int(orig_w * scale)
    new_h = int(orig_h * scale)
    video = video.resized((new_w, new_h))
    x_center = new_w // 2
    y_center = new_h // 2
    video = video.cropped(
        x1=x_center - target_w // 2,
        y1=y_center - target_h // 2,
        x2=x_center + target_w // 2,
        y2=y_center + target_h // 2,
    )

    W, H = video.size  # 1080 x 1920
    clips_to_compose = [video]

    # --- SUBTITLE ---
    chunks = build_word_chunks(segments, start, end)
    for chunk in chunks:
        duration = chunk["end"] - chunk["start"]
        if duration <= 0:
            continue

        img_array = make_text_image(
            text=chunk["text"],
            font_size=70,
            width=W - 80,
            color=(255, 255, 0),  # kuning
            stroke=6,
        )

        subtitle_clip = (
            ImageClip(img_array)
            .with_start(chunk["start"])
            .with_duration(duration)
            .with_position(("center", int(H * 0.60)))
        )
        clips_to_compose.append(subtitle_clip)

    # --- WATERMARK ---
    watermark_array = make_text_image(
        text=f"Source: {source_channel}",
        font_size=50,
        width=W - 80,
        color=(255, 255, 255),  # putih
        stroke=4,
    )
    watermark_clip = (
        ImageClip(watermark_array)
        .with_start(0)
        .with_duration(video.duration)
        .with_position(("center", 20))
    )
    clips_to_compose.append(watermark_clip)

    # Compose dan render
    final = CompositeVideoClip(clips_to_compose)
    output_path = f"{OUTPUT_CLIPS_DIR}/clip_{clip_index}.mp4"
    final.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
    )

    video.close()
    final.close()

    return output_path