"""
Xythe Cloud - Logging
Simple structured logging for the entire application.
"""
import logging
import sys

# Create logger
logger = logging.getLogger("xythe")
logger.setLevel(logging.INFO)

# Console handler
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)

# Format
formatter = logging.Formatter(
    "[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
handler.setFormatter(formatter)

logger.addHandler(handler)