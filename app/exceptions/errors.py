class AppError(Exception):
    status_code: int = 500
    code: str = "INTERNAL_ERROR"
    public_message: str | None = None

    def __init__(
        self,
        message: str,
        payload: dict | None = None,
        public_message: str | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.payload = payload or {}
        self.public_message = public_message or self.public_message or message


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"
    public_message = "We could not find that resource."


class ConflictError(AppError):
    status_code = 409
    code = "CONFLICT"


class ValidationError(AppError):
    status_code = 400
    code = "VALIDATION_ERROR"


class UnauthorizedError(AppError):
    status_code = 401
    code = "UNAUTHORIZED"
    public_message = "Please sign in to continue."


class ForbiddenError(AppError):
    status_code = 403
    code = "FORBIDDEN"
    public_message = "You do not have permission to do that."
