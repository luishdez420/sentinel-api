import logging
import json
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("rlapi")
logger.setLevel(logging.INFO)
logger.propagate = True  # send logs to root handler


def log_event(event: dict):
    # Ensure timestamps are consistent
    event.setdefault("ts", datetime.now(timezone.utc).isoformat())
    logger.info(json.dumps(event))
