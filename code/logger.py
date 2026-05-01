"""
logger.py — Logs all agent decisions to log.txt as required by the hackathon.
"""

import os
import logging
from datetime import datetime

LOG_PATH = os.path.join(os.path.dirname(__file__), "..", "log.txt")

def setup_logger():
    """Setup the chat transcript logger."""
    logger = logging.getLogger("agent_transcript")
    logger.setLevel(logging.DEBUG)

    # File handler
    fh = logging.FileHandler(LOG_PATH, mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(message)s")
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger

def log_ticket(logger, row_index: int, issue: str, subject: str, company: str, result: dict):
    """Log a single ticket processing event."""
    separator = "=" * 70
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    logger.info(f"\n{separator}")
    logger.info(f"TICKET #{row_index} | {timestamp}")
    logger.info(f"{separator}")
    logger.info(f"COMPANY  : {company}")
    logger.info(f"SUBJECT  : {subject or '(none)'}")
    logger.info(f"ISSUE    : {issue[:300]}{'...' if len(issue) > 300 else ''}")
    logger.info(f"---")
    logger.info(f"STATUS        : {result.get('status', 'N/A')}")
    logger.info(f"PRODUCT AREA  : {result.get('product_area', 'N/A')}")
    logger.info(f"REQUEST TYPE  : {result.get('request_type', 'N/A')}")
    logger.info(f"JUSTIFICATION : {result.get('justification', 'N/A')}")
    logger.info(f"RESPONSE      :\n{result.get('response', 'N/A')}")
