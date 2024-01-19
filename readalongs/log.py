"""
log.py: Setup a logger that has colours!
"""

import io
import logging
from contextlib import contextmanager

import coloredlogs

FIELD_STYLES = dict(levelname=dict(color="green"))


def setup_logger(name):
    """Create logger and configure with cool colors!"""
    logger = logging.getLogger(name)

    # Use level='NOTSET' (most permissive) here so whatever level the user later selects
    # does get printed. with level='INFO' here, setting LOGGER.setLevel('DEBUG') in the
    # app doesn't work, and therefore the --debug command line options doesn't work.
    coloredlogs.install(
        level="NOTSET",
        fmt="%(levelname)s - %(message)s",
        logger=logger,
        field_styles=FIELD_STYLES,
    )

    logger.setLevel("INFO")  # default logging level is INFO
    return logger


LOGGER = setup_logger("root")


@contextmanager
def capture_logs():
    """Context manager to capture the logs in a StringIO within the managed context

    Usage:
        with capture_logs() as captured_logs:
            do stuff that logs
        logging_output = captured_log.getvalue()
    """
    log_capture_stream = io.StringIO()
    stream_handler = logging.StreamHandler(log_capture_stream)
    stream_handler.setLevel(logging.INFO)
    old_handlers = list(LOGGER.handlers)
    for x in old_handlers:
        LOGGER.removeHandler(x)  # suppress all existing handlers
    try:
        LOGGER.addHandler(stream_handler)  # capture logging output
        LOGGER.propagate = False  # suppresses logging output to console
        yield log_capture_stream
    finally:
        LOGGER.removeHandler(stream_handler)
        LOGGER.propagate = True
        for x in old_handlers:
            LOGGER.addHandler(x)
