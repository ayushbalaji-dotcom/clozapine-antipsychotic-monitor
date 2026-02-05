import logging
from ..services.task_generator import TaskGenerator
from ..services.notification_engine import NotificationEngine
from ..database import get_sessionmaker

logger = logging.getLogger(__name__)


def daily_task_status_update() -> None:
    logger.info("Starting daily task status update")
    generator = TaskGenerator()
    overdue_count = generator.update_task_statuses()
    reactivated_count = generator.reactivate_expired_waivers()
    SessionLocal = get_sessionmaker()
    db = SessionLocal()
    try:
        notification_count = NotificationEngine(db).process_overdue_tasks()
    finally:
        db.close()
    logger.info("Updated %s tasks to OVERDUE", overdue_count)
    logger.info("Reactivated %s expired waivers", reactivated_count)
    logger.info("Created %s overdue notifications", notification_count)


if __name__ == "__main__":
    daily_task_status_update()
