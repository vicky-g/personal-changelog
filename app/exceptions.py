class AppError(Exception):
    """Base class for all application errors."""

    http_status: int = 500
    default_message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.default_message)
        self.message = message or self.default_message


class EntryNotFound(AppError):
    http_status = 404
    default_message = "Entry not found."


class EntryNotEditable(AppError):
    http_status = 403
    default_message = "Entry is no longer editable (created more than 24 hours ago)."


class SummaryNotFound(AppError):
    http_status = 404
    default_message = "Summary not found."


class NoEntriesFound(AppError):
    http_status = 404
    default_message = "No entries found for the given criteria."
