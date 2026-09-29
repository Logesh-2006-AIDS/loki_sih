from typing import Any, Optional


class AppException(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        details: Optional[Any] = None,
        reason: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details
        self.reason = reason


class InvalidStatusTransitionException(AppException):
    def __init__(self, entity_type: str, current_status: str, target_status: str):
        message = (
            f"Invalid status transition for {entity_type}: "
            f"cannot transition from '{current_status}' to '{target_status}'"
        )
        super().__init__(message=message, status_code=400)


class EntityNotFoundException(AppException):
    def __init__(self, entity_type: str, entity_id: Any):
        super().__init__(message=f"{entity_type} with ID '{entity_id}' not found", status_code=404)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Authentication credentials were not provided or are invalid"):
        super().__init__(message=message, status_code=401)


class ForbiddenException(AppException):
    def __init__(self, message: str = "Operation not permitted for current user role"):
        super().__init__(message=message, status_code=403)


class DuplicateEntityException(AppException):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=409)


class InvalidOperationException(AppException):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=400)


class ValidationException(AppException):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message=message, status_code=400, details=details)


class ConflictException(AppException):
    def __init__(self, message: str):
        super().__init__(message=message, status_code=409)


class QuorumNotMetException(AppException):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message=message, status_code=400, details=details)


class BoundaryTieConflictException(AppException):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message=message, status_code=409, details=details)

