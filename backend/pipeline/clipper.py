from moviepy import VideoFileClip, ImageClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import cv2
import os

OUTPUT_CLIPS_DIR = "outputs/clips"
FONT_PATH = "C:/Windows/Fonts/arialbd.ttf"

FACE_CASCADE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


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


def detect_speaking_face_x(video_path: str, start: float, end: float) -> float | None:
    """
    Sample beberapa frame, deteksi wajah yang sedang bicara
    berdasarkan gerakan mulut. Return ratio posisi X (0.0-1.0).
    """
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    mouth_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_smile.xml")

    sample_times = [start + (end - start) * i / 4 for i in range(5)]
    speaking_positions = []

    for t in sample_times:
        frame_number = int(t * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        if not ret:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame_w = frame.shape[1]

        faces = FACE_CASCADE.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50)
        )

        if len(faces) == 0:
            continue

        for (fx, fy, fw, fh) in faces:
            mouth_roi = gray[fy + fh//2: fy + fh, fx: fx + fw]
            mouths = mouth_cascade.detectMultiScale(
                mouth_roi, scaleFactor=1.1, minNeighbors=8, minSize=(20, 10)
            )
            if len(mouths) > 0:
                face_center_x = fx + fw // 2
                speaking_positions.append(face_center_x / frame_w)

    cap.release()

    if speaking_positions:
        avg = sum(speaking_positions) / len(speaking_positions)
        print(f"Speaker detected at ratio={avg:.2f}")
        return avg

    return None


def get_crop_x(video_path: str, start: float, end: float, orig_w: int, new_w: int, target_w: int) -> int:
    """
    Hitung posisi crop X berdasarkan speaker detection.
    Fallback ke face detection, lalu center crop.
    """
    ratio = detect_speaking_face_x(video_path, start, end)

    if ratio is None:
        # Fallback: deteksi wajah terbesar
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        face_positions = []

        sample_times = [start + (end - start) * i / 4 for i in range(5)]
        for t in sample_times:
            frame_number = int(t * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()
            if not ret:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = FACE_CASCADE.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50)
            )

            if len(faces) > 0:
                largest = max(faces, key=lambda f: f[2] * f[3])
                fx, fw = largest[0], largest[2]
                face_positions.append((fx + fw // 2) / frame.shape[1])

        cap.release()

        if face_positions:
            ratio = sum(face_positions) / len(face_positions)
            print(f"Fallback face detection: ratio={ratio:.2f}")
        else:
            print("No face detected, using center crop")
            return (new_w - target_w) // 2

    face_x = int(ratio * new_w)
    crop_x = face_x - target_w // 2
    crop_x = max(0, min(crop_x, new_w - target_w))
    print(f"Final crop_x={crop_x}")
    return crop_x


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

    video = VideoFileClip(video_path).subclipped(start, end)

    # --- SMART VERTICAL CROP ---
    target_w, target_h = 1080, 1920
    orig_w, orig_h = video.size

    scale = max(target_w / orig_w, target_h / orig_h)
    new_w = int(orig_w * scale)
    new_h = int(orig_h * scale)
    video = video.resized((new_w, new_h))

    crop_x = get_crop_x(video_path, start, end, orig_w, new_w, target_w)
    crop_y = (new_h - target_h) // 2

    video = video.cropped(
        x1=crop_x,
        y1=crop_y,
        x2=crop_x + target_w,
        y2=crop_y + target_h,
    )

    W, H = video.size
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
            color=(255, 255, 0),
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
        text=f"Source: Youtube/{source_channel}",
        font_size=40,
        width=W - 80,
        color=(255, 255, 255),
        stroke=2,
    )
    watermark_clip = (
        ImageClip(watermark_array)
        .with_start(0)
        .with_duration(video.duration)
        .with_position(("center", int(H * 0.90)))
    )
    clips_to_compose.append(watermark_clip)

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