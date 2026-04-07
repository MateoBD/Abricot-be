class AuthException(Exception):
    """
    Raised for authentication and authorization errors.

    Attributes:
        message (str): Human-readable description of the error.
        payload (dict): Optional extra context (e.g., field-level validation errors).
    """

    def __init__(self, message: str, payload: dict | None = None):
        super().__init__(message)
        self.payload = payload or {}
