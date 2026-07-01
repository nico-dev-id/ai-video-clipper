from moviepy import VideoFileClip, ImageClip, CompositeVideoClip, ColorClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os

FONT_PATH = "C:/Windows/Fonts/arialbd.ttf"


def fix_overlapping_clips(clips: list[dict], video_duration: int) -> list[dict]:
    fixed = []
    used_ranges = []
    for clip in clips:
        start = clip["start"]
        end = clip["end"]

        duration = end - start
        if duration < 20 or duration > 120:
            continue

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
    font = ImageFont.truetype(FONT_PATH, font_size)

    dummy = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy)
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    pad = stroke + 10
    img_w = max(width, text_w + pad * 2)
    img_h = text_h + pad * 2

    img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    x = (img_w - text_w) // 2
    y = pad

    draw.text((x, y), text, font=font, fill=(0, 0, 0, 255), stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
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
            "end": min(end - start, chunk_words[-1]["end"] - start),
        })
    return chunks


def create_clip(
    video_path: str,
    clip_info: dict,
    segments: list[dict],
    source_title: str,
    source_channel: str,
    clip_index: int,
    output_dir: str,
) -> str:
    os.makedirs(output_dir, exist_ok=True)

    start = clip_info["start"]
    end = clip_info["end"]

    video = VideoFileClip(video_path).subclipped(start, end)

    # --- LETTERBOX: video landscape utuh di tengah canvas vertical ---
    target_w, target_h = 1080, 1920
    orig_w, orig_h = video.size

    scale = target_w / orig_w
    new_w = target_w
    new_h = int(orig_h * scale)

    video_resized = video.resized((new_w, new_h))

    y_position = (target_h - new_h) // 2

    background = ColorClip(size=(target_w, target_h), color=(0, 0, 0), duration=video.duration)
    video_positioned = video_resized.with_position((0, y_position))

    cropped_video = CompositeVideoClip([background, video_positioned], size=(target_w, target_h))

    W, H = target_w, target_h
    clips_to_compose = [cropped_video]

    # --- SUBTITLE (di bawah video) ---
    chunks = build_word_chunks(segments, start, end)
    subtitle_y = y_position + new_h + 60

    for chunk in chunks:
        duration = chunk["end"] - chunk["start"]
        if duration <= 0:
            continue

        img_array = make_text_image(
            text=chunk["text"],
            font_size=70,
            width=W - 80,
            color=(255, 255, 0),
            stroke=4,
        )

        subtitle_clip = (
            ImageClip(img_array)
            .with_start(chunk["start"])
            .with_duration(duration)
            .with_position(("center", subtitle_y))
        )
        clips_to_compose.append(subtitle_clip)

    # --- WATERMARK (di atas video) ---
    watermark_array = make_text_image(
        text=f"Source: Youtube/{source_channel}",
        font_size=36,
        width=W - 80,
        color=(255, 255, 255),
        stroke=2,
    )
    watermark_clip = (
        ImageClip(watermark_array)
        .with_start(0)
        .with_duration(cropped_video.duration)
        .with_position(("center", int(H * 0.85)))
    )
    clips_to_compose.append(watermark_clip)

    final = CompositeVideoClip(clips_to_compose, size=(target_w, target_h))
    output_path = f"{output_dir}/clip_{clip_index}.mp4"
    final.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
    )

    video.close()
    final.close()

    return output_path