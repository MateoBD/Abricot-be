import logging

import dotenv


class AbricotConsoleFormatter(logging.Formatter):
    """Readable console formatter for local API work."""

    def format(self, record: logging.LogRecord) -> str:
        if getattr(record, "log_style", "") == "api_error":
            return self._format_api_error(record)

        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        source = f"{record.name}:{record.lineno}"
        message = record.getMessage()
        if record.exc_info:
            message = f"{message}\n{self.formatException(record.exc_info)}"
        return f"{timestamp} [{record.levelname:<7}] [{source}] {message}"

    def _format_api_error(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")
        status_code = getattr(record, "api_status_code", "-")
        error_code = getattr(record, "api_error_code", "-")
        method = getattr(record, "api_method", "-")
        path = getattr(record, "api_path", "-")
        query = getattr(record, "api_query", "")
        url = f"{path}?{query}" if query else path
        errors = getattr(record, "api_errors", {}) or {}

        lines = [
            "",
            "============================== [API ERROR] ==============================",
            f"Time    : {timestamp}",
            f"Level   : {record.levelname}",
            f"Status  : {status_code} {error_code}",
            f"Request : {method} {url}",
            f"Origin  : {getattr(record, 'api_origin', '-')}",
            f"Client  : {getattr(record, 'api_client_ip', '-')}",
            f"Public  : {getattr(record, 'api_public_message', '-')}",
            f"Detail  : {_trim(getattr(record, 'api_detail', '-'), 900)}",
        ]
        if errors:
            lines.append(f"Fields  : {_trim(repr(errors), 700)}")
        lines.append(f"Source  : {getattr(record, 'api_source', '-')}")

        if record.exc_info:
            lines.extend(
                [
                    "Trace   :",
                    self.formatException(record.exc_info),
                ]
            )

        lines.append("==========================================================================")
        return "\n".join(lines)


def _filter_maker(level: str):
    level_int = getattr(logging, level)

    def filter(record):
        return record.levelno <= level_int

    return filter


def _env_flag(name: str) -> bool:
    value = dotenv.get_key(dotenv.find_dotenv(), name)
    return bool(value and value.strip().lower() not in {"0", "false", "no", "off"})


def _trim(value: object, max_length: int) -> str:
    text = str(value)
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 3]}..."


_DOTENV_PATH = dotenv.find_dotenv()
_LOGGER_LEVEL = dotenv.get_key(_DOTENV_PATH, "LOGGER_LEVEL") or "INFO"
_CONSOLE_FORMATTER = "pretty" if _env_flag("LOGGER_VERBOSE") else "default"


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "pretty": {
            "()": AbricotConsoleFormatter,
        },
    },
    "filters": {"warnings_and_below": {"()": _filter_maker, "level": "WARNING"}},
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": _LOGGER_LEVEL,
            "formatter": _CONSOLE_FORMATTER,
            "stream": "ext://sys.stdout",
            "filters": ["warnings_and_below"],
        },
        "stderr": {
            "class": "logging.StreamHandler",
            "level": "ERROR",
            "formatter": "pretty",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {"root": {"level": "DEBUG", "handlers": ["console", "stderr"]}},
}
