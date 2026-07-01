import whisper
import os

def transcribe_video(video_path: str) -> dict:
    """
    Transkripsi audio dari video menggunakan Whisper.
    Return: dict berisi segments dan detected_language.
    """
    model = whisper.load_model("base")

    result = model.transcribe(video_path, verbose=False)

    segments = []
    for seg in result["segments"]:
        segments.append({
            "start": round(seg["start"], 2),
            "end": round(seg["end"], 2),
            "text": seg["text"].strip(),
        })

    return {
        "segments": segments,
        "language": result["language"],  # "id", "en", "ar", dll
    }