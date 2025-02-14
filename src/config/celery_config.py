from celery import Celery
from celery.schedules import crontab
from config import get_settings


settings = get_settings()

celery_app = Celery(
    "tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["celery_tasks.tasks"],
)

celery_app.conf.update(
    result_expires=3600,
    timezone="UTC",
    broker_connection_retry_on_startup=True,
)

celery_app.conf.beat_schedule = {
    "delete_expired_tokens_every_hour": {
        "task": "celery_tasks.tasks.delete_expired_token",
        "schedule": crontab(minute=0, hour="*"),
    },
}


if __name__ == "__main__":
    celery_app.start()
