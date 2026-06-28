from groq import Groq
from dotenv import load_dotenv
import os
import json

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def analyze_transcript(segments: list[dict], video_duration: int, num_clips: int = 5) -> list[dict]:
    transcript_text = ""
    for seg in segments:
        transcript_text += f"[{seg['start']}s - {seg['end']}s] {seg['text']}\n"

    prompt = f"""
You are a viral content editor. Analyze this YouTube video transcript and select the {num_clips} BEST segments to clip for short-form content (YouTube Shorts / TikTok).

RULES:
- Each clip must be exactly 60 seconds long (start to start+60)
- Clips must NOT overlap each other AT ALL - minimum gap between clips is 5 seconds
- Sort clips by start time ascending
- Video total duration: {video_duration} seconds
- Start time cannot exceed {video_duration - 60} seconds
- Choose segments with: hooks, emotional moments, valuable insights, funny moments, or surprising facts
- Return ONLY valid JSON, no explanation

TRANSCRIPT:
{transcript_text}

Return exactly {num_clips} clips in this JSON format:
{{
  "clips": [
    {{
      "clip_number": 1,
      "start": 0.0,
      "end": 60.0,
      "reason": "why this segment is engaging"
    }}
  ]
}}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    raw = response.choices[0].message.content
    clean = raw.replace("```json", "").replace("```", "").strip()
    data = json.loads(clean)

    return data["clips"]