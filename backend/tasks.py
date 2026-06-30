from celery_app import celery_app
from pipeline.downloader import download_video
from pipeline.transcriber import transcribe_video
from pipeline.analyzer import analyze_transcript
from pipeline.clipper import fix_overlapping_clips, create_clip

@celery_app.task(bind=True)
def generate_clips_task(self, url: str, num_clips: int = 5):
    try:
        # Step 1: Download (0-20%)
        self.update_state(state="PROGRESS", meta={
            "status": "Downloading video from YouTube...",
            "percent": 5,
        })
        video_info = download_video(url)
        self.update_state(state="PROGRESS", meta={
            "status": f"Download complete: {video_info['title'][:50]}",
            "percent": 20,
        })

        # Step 2: Transcribe (20-50%)
        self.update_state(state="PROGRESS", meta={
            "status": "Transcribing audio with Whisper AI...",
            "percent": 25,
        })
        segments = transcribe_video(video_info["video_path"])
        self.update_state(state="PROGRESS", meta={
            "status": f"Transcription complete: {len(segments)} segments found",
            "percent": 50,
        })

        # Step 3: Analyze (50-65%)
        self.update_state(state="PROGRESS", meta={
            "status": "AI analyzing best segments...",
            "percent": 55,
        })
        clips = analyze_transcript(segments, video_info["duration"], num_clips=num_clips)
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

        # Step 4: Render clips (65-100%)
        results = []
        for i, clip in enumerate(clips):
            percent = 65 + int((i / len(clips)) * 35)
            self.update_state(state="PROGRESS", meta={
                "status": f"Rendering clip {i+1} of {len(clips)}...",
                "percent": percent,
            })
            path = create_clip(
                video_path=video_info["video_path"],
                clip_info=clip,
                segments=segments,
                source_title=video_info["title"],
                source_channel=video_info["channel"],
                clip_index=i + 1,
            )
            results.append({
                "clip_number": i + 1,
                "start": clip["start"],
                "end": clip["end"],
                "reason": clip["reason"],
                "url": f"/clips/clip_{i + 1}.mp4",
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