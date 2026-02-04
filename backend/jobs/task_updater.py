import logging
from ..services.task_generator import TaskGenerator

logger = logging.getLogger(__name__)


def daily_task_status_update() -> None:
    logger.info("Starting daily task status update")
    generator = TaskGenerator()
    overdue_count = generator.update_task_statuses()
    reactivated_count = generator.reactivate_expired_waivers()
    logger.info("Updated %s tasks to OVERDUE", overdue_count)
    logger.info("Reactivated %s expired waivers", reactivated_count)


if __name__ == "__main__":
    daily_task_status_update()
