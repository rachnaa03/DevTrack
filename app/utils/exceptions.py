class DevTrackException(Exception):
    """Base exception class for all custom application-level errors."""
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)

class EmailAlreadyExistsException(DevTrackException):
    """Raised when attempting to register a user with an already registered email."""
    def __init__(self) -> None:
        super().__init__(
            code="EMAIL_ALREADY_EXISTS",
            message="User with this email is already registered.",
            status_code=400
        )

class InvalidCredentialsException(DevTrackException):
    """Raised when login authentication fails due to bad credentials."""
    def __init__(self) -> None:
        super().__init__(
            code="AUTHENTICATION_FAILED",
            message="Invalid email or password.",
            status_code=401
        )

class AuthenticationException(DevTrackException):
    """Raised when JWT validation or extraction fails."""
    def __init__(self) -> None:
        super().__init__(
            code="AUTHENTICATION_FAILED",
            message="Could not validate credentials.",
            status_code=401
        )


