import sys
from pathlib import Path
from loguru import logger
from utils.config import settings

logger.remove()


log_dir = Path(settings.log_file).parent
log_dir.mkdir(parents=True, exist_ok=True)


logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level=settings.log_level,
    colorize=True
)


logger.add(
    settings.log_file,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level=settings.log_level,
    rotation="10 MB",
    retention="30 days",
    compression="zip"
)

def get_logger(name: str):
    return logger.bind(name=name)