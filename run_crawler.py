#!/usr/bin/env python3
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from crawler.book_crawler import run_crawler
from utils.logger import get_logger

logger = get_logger(__name__)


def main():
    logger.info("Starting Book Crawler...")

    try:
        resume = "--resume" in sys.argv

        if resume:
            logger.info("Resume mode enabled")

        asyncio.run(run_crawler(resume=resume))

        logger.info("Crawler completed successfully!")

    except KeyboardInterrupt:
        logger.info("Crawler interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Crawler failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()