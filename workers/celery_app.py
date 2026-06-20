import os
from celery import Celery
from celery.schedules import crontab

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "bharatllm_workers",
    broker=REDIS_URL,
    backend=REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kolkata",
    enable_utc=True,
    result_expires=86400, # 24 Hours
    task_always_eager=False
)

celery_app.conf.beat_schedule = {
    "scrape-finance-circulars-midnight": {
        "task": "workers.scheduled_tasks.scrape_finance_circulars",
        "schedule": crontab(hour=23, minute=30),
    },
    "scrape-legal-judgements-midnight": {
        "task": "workers.scheduled_tasks.scrape_legal_judgements",
        "schedule": crontab(hour=23, minute=45),
    },
}
