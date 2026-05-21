import logging
import sys
from typing import cast

import structlog


def configure_logging() -> None:
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=False)

    shared_processors: list[structlog.typing.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        timestamper,
    ]

    logging.basicConfig(
        format="%(message)s",
        level=logging.INFO,
        stream=sys.stdout,
    )

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger() -> structlog.stdlib.BoundLogger:
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger())
