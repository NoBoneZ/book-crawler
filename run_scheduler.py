#!/usr/bin/env python3

import asyncio
import sys
import signal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from scheduler.book_scheduler import BookScheduler
from utils.logger import get_logger

logger = get_logger(__name__)

scheduler = None


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    logger.info(f"Received signal {signum}, shutting down...")
    if scheduler:
        scheduler.stop()
    sys.exit(0)


def main():
    """Main function"""
    global scheduler

    logger.info("Starting Book Scheduler...")

    try:
        # Check if we should run once or continuously
        run_once = "--once" in sys.argv

        scheduler = BookScheduler()

        if run_once:
            logger.info("Running scheduler once...")
            asyncio.run(scheduler.scheduled_crawl_and_detect())
            logger.info("Scheduler run completed!")
        else:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            scheduler.start()

            logger.info("Scheduler is running. Press Ctrl+C to stop.")

            try:
                while True:
                    asyncio.get_event_loop().run_until_complete(asyncio.sleep(1))
            except KeyboardInterrupt:
                logger.info("Scheduler interrupted by user")
                scheduler.stop()

    except Exception as e:
        logger.error(f"Scheduler failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()