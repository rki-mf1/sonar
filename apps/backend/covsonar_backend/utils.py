import logging

from django.utils.timezone import now
import json_log_formatter


class CustomisedJSONFormatter(json_log_formatter.JSONFormatter):
    def json_record(self, message: str, extra: dict, record: logging.LogRecord):
        extra["filename"] = record.filename
        extra["funcName"] = record.funcName

        extra["secs"] = round(record.msecs / 1000, 4)
        if record.exc_info:
            extra["exc_info"] = self.formatException(record.exc_info)

        return {
            "app": "sonar-backend",
            "message": message,
            "timestamp": now().isoformat(),
            "level": record.levelname,
            "context": extra,
        }
