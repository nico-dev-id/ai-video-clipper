from celery_app import celery_app
from pipeline.downloader import download_video
from pipeline.transcriber import transcribe_video
from pipeline.analyzer import analyze_transcript, generate_hook_text, translate_segments_to_indonesian
from pipeline.clipper import fix_overlapping_clips, create_clip
from pipeline.thumbnail import generate_thumbnail

@celery_app.task(bind=True)
def generate_clips_task(self, url: str, num_clips: int = 5):
    try:
        self.update_state(state="PROGRESS", meta={
            "status": "Downloading video from YouTube...",
            "percent": 5,
        })
        video_info = download_video(url)
        video_id = video_info["video_id"]
        clips_dir = f"{video_info['output_dir']}/clips"
        thumbnails_dir = f"{video_info['output_dir']}/thumbnails"

        self.update_state(state="PROGRESS", meta={
            "status": f"Download complete: {video_info['title'][:50]}",
            "percent": 20,
        })

        self.update_state(state="PROGRESS", meta={
            "status": "Transcribing audio with Whisper AI...",
            "percent": 25,
        })

        transcribe_result = transcribe_video(video_info["video_path"])
        segments_original = transcribe_result["segments"]
        detected_language = transcribe_result["language"]

        self.update_state(state="PROGRESS", meta={
            "status": f"Transcription complete: {len(segments_original)} segments ({detected_language})",
            "percent": 50,
        })

        # Translate ke Indonesia kalau bukan bahasa Indonesia
        if detected_language != "id":
            self.update_state(state="PROGRESS", meta={
                "status": f"Translating from {detected_language.upper()} to Bahasa Indonesia...",
                "percent": 52,
            })
            segments_translated = translate_segments_to_indonesian(segments_original)
            self.update_state(state="PROGRESS", meta={
                "status": "Translation complete!",
                "percent": 54,
            })
        else:
            segments_translated = segments_original

        self.update_state(state="PROGRESS", meta={
            "status": "AI analyzing best segments...",
            "percent": 55,
        })

        # Analyze pakai transcript original
        clips = analyze_transcript(segments_original, video_info["duration"], num_clips=num_clips)
        clips = fix_overlapping_clips(clips, video_info["duration"])

        self.update_state(state="PROGRESS", meta={
            "status": f"Analysis complete: {len(clips)} clips selected",
            "percent": 65,
        })

        if not clips:
            return {
                "status": "error",
                "error": "No clips could be generated. Possible cause: AI rate limit reached. Please try again later.",
            }

        results = []
        for i, clip in enumerate(clips):
            percent = 65 + int((i / len(clips)) * 30)

            # Generate hook dulu sebelum render
            self.update_state(state="PROGRESS", meta={
                "status": f"AI generating content for clip {i+1}...",
                "percent": percent,
            })
            clip_segments_text = " ".join(
                s["text"] for s in segments_original
                if s["end"] > clip["start"] and s["start"] < clip["end"]
            )
            hook_data = generate_hook_text(clip_segments_text)

            # Render clip
            self.update_state(state="PROGRESS", meta={
                "status": f"Rendering clip {i+1} of {len(clips)}...",
                "percent": percent + 2,
            })
            path = create_clip(
                video_path=video_info["video_path"],
                clip_info=clip,
                segments=segments_translated,
                source_title=video_info["title"],
                source_channel=video_info["channel"],
                clip_index=i + 1,
                output_dir=clips_dir,
                hook_data=hook_data,
            )

            # Generate thumbnail
            self.update_state(state="PROGRESS", meta={
                "status": f"Generating thumbnail for clip {i+1}...",
                "percent": percent + 4,
            })
            thumbnail_path = generate_thumbnail(
                path,
                hook_data,
                i + 1,
                thumbnails_dir,
                source_video_path=video_info["video_path"],
                clip_start=clip["start"],
            )

            results.append({
                "clip_number": i + 1,
                "start": clip["start"],
                "end": clip["end"],
                "reason": clip["reason"],
                "title": hook_data["title"],
                "hook": hook_data["hook"],
                "benefit": hook_data["benefit"],
                "description": hook_data["description"],
                "hashtags": hook_data["hashtags"],
                "url": f"/outputs/{video_id}/clips/clip_{i + 1}.mp4",
                "thumbnail_url": f"/outputs/{video_id}/thumbnails/thumbnail_{i + 1}.jpg",
            })

        return {
            "status": "done",
            "video_title": video_info["title"],
            "channel": video_info["channel"],
            "duration": video_info["duration"],
            "clips": results,
        }

    except Exception as e:
        self.update_state(state="FAILURE", meta={
            "status": str(e),
            "percent": 0,
        })
        return {"status": "error", "error": str(e)}