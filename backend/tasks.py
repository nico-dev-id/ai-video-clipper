from celery_app import celery_app
from pipeline.downloader import download_video
from pipeline.transcriber import transcribe_video
from pipeline.analyzer import analyze_transcript
from pipeline.clipper import fix_overlapping_clips, create_clip

@celery_app.task(bind=True)
def generate_clips_task(self, url: str, num_clips: int = 5):
    try:
        # Step 1
        self.update_state(state="PROGRESS", meta={"status": "Downloading video...", "step": 1, "total": 4})
        video_info = download_video(url)

        # Step 2
        self.update_state(state="PROGRESS", meta={"status": "Transcribing audio...", "step": 2, "total": 4})
        segments = transcribe_video(video_info["video_path"])

        # Step 3
        self.update_state(state="PROGRESS", meta={"status": "AI analyzing best segments...", "step": 3, "total": 4})
        clips = analyze_transcript(segments, video_info["duration"], num_clips=num_clips)
        clips = fix_overlapping_clips(clips, video_info["duration"])

        # Step 4
        results = []
        for i, clip in enumerate(clips):
            self.update_state(
                state="PROGRESS",
                meta={"status": f"Rendering clip {i+1} of {len(clips)}...", "step": 4, "total": 4}
            )
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
        self.update_state(state="FAILURE", meta={"status": str(e)})
        raise