from pipeline.transcriber import transcribe_video

segments = transcribe_video("outputs/dQw4w9WgXcQ.mp4")

for seg in segments[:5]:  # tampilkan 5 segment pertama saja
    print(seg)