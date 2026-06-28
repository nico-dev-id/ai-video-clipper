from groq import Groq
from dotenv import load_dotenv
import os
import json
import time

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MAX_CHARS_PER_CHUNK = 6000


def score_chunks(chunks: list[dict]) -> list[dict]:
    scored = []

    for i, chunk in enumerate(chunks):
        prompt = f"""
You are a viral content editor for YouTube Shorts. Rate this transcript segment strictly from 1-10 for viral potential.

Scoring guide:
- 9-10: Extremely viral — shocking revelation, emotional breakdown, controversial opinion, or surprising fact
- 7-8: Very engaging — strong story, valuable insight, or funny moment
- 5-6: Moderate — decent content but nothing special
- 3-4: Low — mostly filler, transitions, or repetitive content
- 1-2: Skip — closing remarks, greetings, subscribe reminders

Be strict and discriminating. Most segments should score 4-6, only truly exceptional ones get 8+.

TRANSCRIPT SEGMENT ({chunk['time_range']}):
{chunk['text']}

Return ONLY this JSON:
{{
  "score": 6,
  "reason": "one sentence why"
}}
"""
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            raw = response.choices[0].message.content
            clean = raw.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean)

            scored.append({
                **chunk,
                "score": data.get("score", 5),
                "score_reason": data.get("reason", ""),
            })
        except Exception as e:
            scored.append({**chunk, "score": 3, "score_reason": f"scoring failed: {str(e)}"})

        # Delay antar API call supaya tidak hit rate limit
        time.sleep(2)

    return scored


def build_chunks(segments: list[dict], video_duration: int) -> list[dict]:
    full_text = ""
    for seg in segments:
        full_text += f"[{seg['start']}s - {seg['end']}s] {seg['text']}\n"

    lines = full_text.split("\n")
    chunks = []
    current_text = ""
    current_start = None
    current_end = None

    for line in lines:
        if not line.strip():
            continue

        try:
            time_part = line.split("]")[0].replace("[", "")
            start_t = float(time_part.split("s -")[0].strip())
            end_t = float(time_part.split("- ")[1].replace("s", "").strip())
        except Exception:
            continue

        if current_start is None:
            current_start = start_t

        current_text += line + "\n"
        current_end = end_t

        if len(current_text) >= MAX_CHARS_PER_CHUNK:
            chunks.append({
                "text": current_text,
                "start": current_start,
                "end": current_end,
                "time_range": f"{int(current_start)}s - {int(current_end)}s",
            })
            current_text = ""
            current_start = None
            current_end = None

    if current_text and current_start is not None:
        chunks.append({
            "text": current_text,
            "start": current_start,
            "end": current_end,
            "time_range": f"{int(current_start)}s - {int(current_end)}s",
        })

    return chunks


def pick_clips_from_chunk(chunk: dict, num_clips: int, video_duration: int) -> list[dict]:
    prompt = f"""
You are a viral content editor. From this transcript segment, select {num_clips} best 60-second clip.

RULES:
- Each clip must be exactly 60 seconds (start to start+60)
- Clips must NOT overlap - minimum 5 second gap
- start cannot exceed {video_duration - 60} seconds
- Only pick timestamps within: {chunk['time_range']}
- Return ONLY valid JSON

TRANSCRIPT:
{chunk['text']}

Return:
{{
  "clips": [
    {{
      "clip_number": 1,
      "start": 10.0,
      "end": 70.0,
      "reason": "why this is engaging"
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
    time.sleep(2)
    return data["clips"]


def analyze_transcript(segments: list[dict], video_duration: int, num_clips: int = 5) -> list[dict]:
    # Step 1: Build chunks
    chunks = build_chunks(segments, video_duration)

    if not chunks:
        return []

    if len(chunks) == 1:
        return pick_clips_from_chunk(chunks[0], num_clips, video_duration)

    # Step 2: Score semua chunks
    scored_chunks = score_chunks(chunks)

    # Debug
    print("\n=== CHUNK SCORES ===")
    for c in scored_chunks:
        print(f"[{c['time_range']}] score: {c['score']} — {c['score_reason']}")
    print("====================\n")

    # Step 3: Sort by score, ambil top chunks
    scored_chunks.sort(key=lambda x: x["score"], reverse=True)
    top_chunks = scored_chunks[:num_clips]
    top_chunks.sort(key=lambda x: x["start"])

    # Step 4: Pick 1 clip per top chunk
    all_clips = []
    clip_number = 1
    for chunk in top_chunks:
        try:
            clips = pick_clips_from_chunk(chunk, 1, video_duration)
            for clip in clips:
                clip["clip_number"] = clip_number
                all_clips.append(clip)
                clip_number += 1
        except Exception as e:
            print(f"Failed to pick clip from chunk {chunk['time_range']}: {e}")
            continue

    return all_clips