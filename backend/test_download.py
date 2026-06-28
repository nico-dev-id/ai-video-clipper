from pipeline.downloader import download_video

url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # video pendek untuk test
result = download_video(url)
print(result)