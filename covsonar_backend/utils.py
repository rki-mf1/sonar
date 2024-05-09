import json_log_formatter
import logging
from django.utils.timezone import now

class CustomisedJSONFormatter(json_log_formatter.JSONFormatter):
    def json_record(self, message: str, extra: dict, record: logging.LogRecord):
        extra['filename'] = record.filename
        extra['funcName'] = record.funcName
        extra['secs'] = round(record.msecs/1000, 4)
        if record.exc_info:
            extra['exc_info'] = self.formatException(record.exc_info)

        return {
            'message': message,
            'timestamp': now().isoformat(),
            'level': record.levelname,
            'context': extra
        }