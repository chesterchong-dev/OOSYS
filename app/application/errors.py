"""Expected application failures that adapters can map to transport responses."""


class ApplicationError(Exception):
    """Base for expected use-case failures with a safe public contract."""

    code = "application_error"
    message = "The operation could not be completed."
    status_code = 400

    def __init__(self) -> None:
        super().__init__(self.message)


class ResourceNotFound(ApplicationError):
    """The requested resource does not exist or is not visible to the caller."""

    code = "not_found"
    message = "Resource not found."
    status_code = 404


class OperationConflict(ApplicationError):
    """The operation conflicts with the current resource state."""

    code = "conflict"
    message = "The operation conflicts with the current state."
    status_code = 409


class OperationForbidden(ApplicationError):
    """The authenticated caller is not permitted to perform the operation."""

    code = "forbidden"
    message = "The operation is not permitted."
    status_code = 403
