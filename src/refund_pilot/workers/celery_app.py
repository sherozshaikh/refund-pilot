from celery import Celery

from refund_pilot.core.config import Settings
from refund_pilot.core.telemetry import configure_telemetry

configure_telemetry()

_settings = Settings()

app = Celery(
    "refund_pilot",
    broker=_settings.redis_url,
    backend=_settings.redis_url,
    include=["refund_pilot.workers.tasks"],
)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_max_tasks_per_child=100,
)
