from pipeline.transcriber import transcribe_video
from pipeline.analyzer import analyze_transcript
from pipeline.clipper import fix_overlapping_clips, create_clip

video_path = "outputs/dQw4w9WgXcQ.mp4"
video_duration = 213

segments = transcribe_video(video_path)
clips = analyze_transcript(segments, video_duration)
clips = fix_overlapping_clips(clips, video_duration)

print(f"Jumlah clip valid: {len(clips)}")

for i, clip in enumerate(clips):
    print(f"\nMemproses clip {i+1}: {clip['start']}s - {clip['end']}s")
    path = create_clip(
        video_path=video_path,
        clip_info=clip,
        segments=segments,
        source_title="Rick Astley - Never Gonna Give You Up",
        source_channel="Rick Astley",
        clip_index=i+1,
    )
    print(f"Saved: {path}")