class ServiceError(Exception):
    """Base class for business-logic errors. Services know nothing about HTTP."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(ServiceError):
    pass


class AlreadyExistsError(ServiceError):
    pass


class AuthenticationError(ServiceError):
    pass


class PermissionDeniedError(ServiceError):
    pass


class BusinessRuleError(ServiceError):
    """The request is valid but breaks a business rule (e.g. already premium)."""