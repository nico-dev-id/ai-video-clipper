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
You are a viral content editor. From this transcript segment, select {num_clips} best clip for YouTube Shorts.

RULES:
- Clip duration should be between 30-90 seconds (flexible, not fixed)
- IMPORTANT: End the clip at a natural breakpoint - finish the sentence or thought, don't cut mid-sentence
- Start the clip at a natural beginning - start of a sentence or thought, not mid-sentence
- start cannot exceed {video_duration - 30} seconds
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
      "end": 65.0,
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
    chunks = build_chunks(segments, video_duration)

    if not chunks:
        return []

    if len(chunks) == 1:
        print("DEBUG: only 1 chunk, picking directly")
        result = pick_clips_from_chunk(chunks[0], num_clips, video_duration)
        print(f"DEBUG: clips returned = {result}")
        return result

    scored_chunks = score_chunks(chunks)

    print("\n=== CHUNK SCORES ===")
    for c in scored_chunks:
        print(f"[{c['time_range']}] score: {c['score']} — {c['score_reason']}")
    print("====================\n")

    scored_chunks.sort(key=lambda x: x["score"], reverse=True)
    top_chunks = scored_chunks[:num_clips]
    top_chunks.sort(key=lambda x: x["start"])

    all_clips = []
    clip_number = 1
    for chunk in top_chunks:
        try:
            print(f"Picking clip from chunk: {chunk['time_range']}")
            clips = pick_clips_from_chunk(chunk, 1, video_duration)
            print(f"Got clips: {clips}")
            for clip in clips:
                clip["clip_number"] = clip_number
                all_clips.append(clip)
                clip_number += 1
        except Exception as e:
            print(f"FAILED chunk {chunk['time_range']}: {e}")
            continue

    print(f"Total clips collected: {len(all_clips)}")
    return all_clips

def generate_hook_text(clip_text: str) -> dict:
    """Generate hook, benefit, description, dan hashtag untuk tiap clip."""
    prompt = f"""
You are a viral YouTube Shorts content strategist for Indonesian audience. Based on this transcript, generate content for a YouTube Shorts post.

Return ONLY this JSON, no explanation:
{{
  "title": "catchy SEO-friendly video title in Indonesian, max 60 characters, no clickbait but intriguing",
  "hook": "provocative question or shocking statement max 5 words in Indonesian",
  "benefit": "what viewer will gain max 5 words in Indonesian",
  "description": "2-3 sentences in Indonesian that feels relatable to daily life, creates emotional connection, and makes people want to watch. End with a call to action.",
  "hashtags": "#hashtag1 #hashtag2 #hashtag3 #hashtag4 #hashtag5 #hashtag6 #hashtag7 #hashtag8"
}}

Rules:
- title: max 60 characters, SEO-friendly, natural Indonesian, intriguing but not misleading
- hook and benefit: SHORT, max 5 words, ALL CAPS, provocative
- description: conversational Indonesian, relatable, emotional, end with CTA
- hashtags: mix of Indonesian viral hashtags + topic-specific, 8 hashtags total

TRANSCRIPT:
{clip_text}
"""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
        )
        raw = response.choices[0].message.content
        clean = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean)
        time.sleep(1)
        return {
            "title": data.get("title", ""),
            "hook": data.get("hook", "RAHASIA TERUNGKAP"),
            "benefit": data.get("benefit", "HIDUP BERUBAH SETELAH INI"),
            "description": data.get("description", ""),
            "hashtags": data.get("hashtags", "#shorts #viral #fyp #indonesia"),
        }
    except Exception:
        return {
            "title": "",
            "hook": "RAHASIA TERUNGKAP",
            "benefit": "HIDUP BERUBAH SETELAH INI",
            "description": "",
            "hashtags": "#shorts #viral #fyp #indonesia",
        }

def translate_segments_to_indonesian(segments: list[dict]) -> list[dict]:
    """
    Translate segments ke Bahasa Indonesia dalam 1 API call.
    Kirim semua teks sekaligus, hemat token.
    """
    # Gabungkan semua teks dengan separator unik
    combined = "\n".join([f"[{i}] {seg['text']}" for i, seg in enumerate(segments)])

    prompt = f"""Translate ALL of the following text segments to natural Bahasa Indonesia.
Keep the [number] prefix exactly as is. Only translate the text after the prefix.
Return ONLY the translated lines, nothing else.

{combined}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        raw = response.choices[0].message.content.strip()
        lines = raw.split("\n")

        translated = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Parse [index] text
            if line.startswith("[") and "]" in line:
                idx_end = line.index("]")
                try:
                    idx = int(line[1:idx_end])
                    text = line[idx_end+1:].strip()
                    if idx < len(segments):
                        translated.append({
                            "start": segments[idx]["start"],
                            "end": segments[idx]["end"],
                            "text": text,
                        })
                except ValueError:
                    continue

        # Fallback kalau translate gagal atau tidak lengkap
        if len(translated) < len(segments) * 0.5:
            return segments

        time.sleep(2)
        return translated

    except Exception as e:
        print(f"Translation failed: {e}")
        return segments  # fallback ke original