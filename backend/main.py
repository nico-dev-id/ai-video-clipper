from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from tasks import generate_clips_task
from celery.result import AsyncResult
from celery_app import celery_app

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("outputs", exist_ok=True)
app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

class GenerateRequest(BaseModel):
    url: str
    num_clips: int = 5

@app.post("/api/generate-clips")
def generate_clips(request: GenerateRequest):
    task = generate_clips_task.delay(request.url, request.num_clips)
    return {"task_id": task.id}

@app.get("/api/status/{task_id}")
def get_status(task_id: str):
    result = AsyncResult(task_id, app=celery_app)

    if result.state == "PENDING":
        return {"state": "PENDING", "status": "Waiting in queue...", "percent": 0}
    elif result.state == "PROGRESS":
        info = result.info or {}
        return {
            "state": "PROGRESS",
            "status": info.get("status", ""),
            "percent": info.get("percent", 0),
        }
    elif result.state == "SUCCESS":
        return {"state": "SUCCESS", "result": result.result}
    elif result.state == "FAILURE":
        return {"state": "FAILURE", "status": str(result.info)}
    else:
        return {"state": result.state, "status": "Processing...", "percent": 0}

@app.get("/")
def root():
    return {"status": "AI Video Clipper API is running"}