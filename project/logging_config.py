"""
Creates the logging configuration for the application.
"""

import logging

import dotenv


def filter_maker(level):
    level = getattr(logging, level)

    def filter(record):
        return record.levelno <= level

    return filter


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s %(levelname)8s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "verbose": {
            "format": "%(asctime)s %(levelname)8s: %(message)s [in %(pathname)s:%(lineno)d]",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "filters": {"warnings_and_below": {"()": filter_maker, "level": "WARNING"}},
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": dotenv.get_key(dotenv.find_dotenv(), "LOGGER_LEVEL") or "INFO",
            "formatter": "verbose"
            if (dotenv.get_key(dotenv.find_dotenv(), "LOGGER_VERBOSE"))
            else "default",
            "stream": "ext://sys.stdout",
            "filters": ["warnings_and_below"],
        },
        "stderr": {
            "class": "logging.StreamHandler",
            "level": "ERROR",
            "formatter": "verbose",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {"root": {"level": "DEBUG", "handlers": ["console", "stderr"]}},
}
