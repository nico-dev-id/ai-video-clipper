from PIL import Image, ImageDraw, ImageFont
from moviepy import VideoFileClip
import os

FONT_PATH = "C:/Windows/Fonts/arialbd.ttf"


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] > max_width:
            if current_line:
                lines.append(current_line)
            current_line = word
        else:
            current_line = test_line
    if current_line:
        lines.append(current_line)

    return lines


def draw_text_block(draw, text, font_path, W, max_width, area_top, area_height, font_size_start):
    font_size = font_size_start

    while font_size > int(W * 0.06):
        font = ImageFont.truetype(font_path, font_size)
        lines = wrap_text(draw, text.upper(), font, max_width)
        if len(lines) <= 3:
            break
        font_size -= 5

    font = ImageFont.truetype(font_path, font_size)
    lines = wrap_text(draw, text.upper(), font, max_width)

    line_height = font_size + 20
    total_text_height = len(lines) * line_height
    start_y = area_top + (area_height - total_text_height) // 2

    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (W - text_w) // 2
        y = start_y + i * line_height

        # Teks kuning dengan stroke hitam tebal — tidak ada background
        draw.text(
            (x, y),
            line,
            font=font,
            fill=(255, 220, 0),       # kuning
            stroke_width=6,
            stroke_fill=(0, 0, 0),    # stroke hitam
        )


def generate_thumbnail(clip_path: str, hook_data: dict, clip_index: int, output_dir: str, source_video_path: str = None, clip_start: float = 0) -> str:
    os.makedirs(output_dir, exist_ok=True)

    # Ambil frame dari video ORIGINAL (tanpa subtitle) kalau tersedia
    if source_video_path and os.path.exists(source_video_path):
        video = VideoFileClip(source_video_path)
        # Sample di pertengahan clip
        sample_time = clip_start + (video.duration - clip_start) / 4
        sample_time = min(sample_time, video.duration - 1)
        frame = video.get_frame(sample_time)
        video.close()
    else:
        video = VideoFileClip(clip_path)
        mid_time = video.duration / 2
        frame = video.get_frame(mid_time)
        video.close()

    img = Image.fromarray(frame).convert("RGB")
    W, H = img.size

    # Resize ke 1080x1920 letterbox (sama seperti clip)
    target_w, target_h = 1080, 1920
    orig_w, orig_h = W, H
    scale = target_w / orig_w
    new_w = target_w
    new_h = int(orig_h * scale)

    img = img.resize((new_w, new_h), Image.LANCZOS)

    # Buat canvas hitam
    canvas = Image.new("RGB", (target_w, target_h), (0, 0, 0))
    y_position = (target_h - new_h) // 2
    canvas.paste(img, (0, y_position))
    img = canvas
    W, H = target_w, target_h

    draw = ImageDraw.Draw(img)

    max_width = W - 120
    font_size_start = int(W * 0.10)

    # Area hitam ATAS — hook text
    top_area_height = int(H * 0.28)
    draw_text_block(
        draw=draw,
        text=hook_data["hook"],
        font_path=FONT_PATH,
        W=W,
        max_width=max_width,
        area_top=60,
        area_height=top_area_height - 20,
        font_size_start=font_size_start,
    )

    # Area hitam BAWAH — benefit text
    bottom_area_top = y_position + new_h + 20
    bottom_area_height = H - bottom_area_top - 20
    draw_text_block(
        draw=draw,
        text=hook_data["benefit"],
        font_path=FONT_PATH,
        W=W,
        max_width=max_width,
        area_top=bottom_area_top,
        area_height=bottom_area_height,
        font_size_start=font_size_start,
    )

    output_path = f"{output_dir}/thumbnail_{clip_index}.jpg"
    img.save(output_path, quality=95)

    return output_path