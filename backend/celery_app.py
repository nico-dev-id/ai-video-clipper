from celery import Celery
from dotenv import load_dotenv
import ssl
import os

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")

celery_app = Celery(
    "ai_video_clipper",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    broker_use_ssl={
        "ssl_cert_reqs": ssl.CERT_NONE,
    },
    redis_backend_use_ssl={
        "ssl_cert_reqs": ssl.CERT_NONE,
    },
)