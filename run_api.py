#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import uvicorn
from utils.config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


def main():
    logger.info(f"Starting API server on {settings.api_host}:{settings.api_port}")
    logger.info(f"API documentation: http://{settings.api_host}:{settings.api_port}/docs")
    logger.info(f"API key: {settings.api_key}")

    try:
        uvicorn.run(
            "api.main:app",
            host=settings.api_host,
            port=settings.api_port,
            reload=True if "--reload" in sys.argv else False,
            log_level=settings.log_level.lower(),
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("API server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"API server failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()