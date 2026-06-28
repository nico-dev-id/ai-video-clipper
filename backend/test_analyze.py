from pipeline.transcriber import transcribe_video
from pipeline.analyzer import analyze_transcript

segments = transcribe_video("outputs/dQw4w9WgXcQ.mp4")
clips = analyze_transcript(segments, video_duration=213)

for clip in clips:
    print(clip)