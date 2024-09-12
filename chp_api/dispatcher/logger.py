import datetime

class LogEntry():
    def __init__(self, level, message, code=None, timestamp=None):
        if timestamp is None:
            self.timestamp = datetime.datetime.utcnow().isoformat()
        else:
            self.timestamp = timestamp
        self.level = level
        self.message = message
        self.code = code

    def to_dict(self):
        return {
                "timestamp": self.timestamp,
                "level": self.level,
                "message": self.message,
                "code": self.code,
                }

    @staticmethod
    def load_log(log_dict):
        timestamp = log_dict.pop("timestamp")
        level = log_dict.pop("level")
        message = log_dict.pop("message")
        code = log_dict.pop("code")
        return LogEntry(
                level,
                message,
                code=code,
                timestamp=timestamp,
                )


class Logger():
    def __init__(self):
        self.logs = []

    def add_log(self, level, message, code=None):
        self.logs.append(
                LogEntry(
                    level,
                    message,
                    code,
                    )
                )
    
    def add_logs(self, logs):
        for log in logs:
            self.logs.append(LogEntry.load_log(log))

    def info(self, message, code=None):
        self.add_log('INFO', message, code)

    def debug(self, message, code=None):
        self.add_log('DEBUG', message, code)

    def warning(self, message, code=None):
        self.add_log('WARNING', message, code)

    def error(self, message, code=None):
        self.add_log('ERROR', message, code)

    def to_dict(self):
        logs = [log.to_dict() for log in self.logs]
        return logs 
