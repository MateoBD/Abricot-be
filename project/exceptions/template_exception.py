"""Custom exception class for errors; can include additional payload data"""


class TemplateException(Exception):
    def __init__(self, message, payload=None):
        super().__init__(message)
        self.payload = payload or {}
