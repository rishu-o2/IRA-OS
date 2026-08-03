class LoggingError(Exception):
    """Base exception for the logging subsystem."""
    pass

class SinkError(LoggingError):
    """Raised when a log sink fails to write."""
    pass

class FormatterError(LoggingError):
    """Raised when a formatter fails to render a LogEntry."""
    pass
