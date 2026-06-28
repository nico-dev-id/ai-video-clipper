import whisper
import os

def transcribe_video(video_path: str) -> list[dict]:
    """
    Transkripsi audio dari video menggunakan Whisper.
    Return: list of segments, masing-masing berisi start, end, text.
    """
    model = whisper.load_model("base")  # 'base' cukup cepat untuk testing

    result = model.transcribe(video_path, verbose=False)

    segments = []
    for seg in result["segments"]:
        segments.append({
            "start": round(seg["start"], 2),
            "end": round(seg["end"], 2),
            "text": seg["text"].strip(),
        })

    return segments