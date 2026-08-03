from enum import IntEnum

class LogLevel(IntEnum):
    """
    Log severity levels in ascending order.
    Integer values allow numeric comparison (e.g., level >= LogLevel.WARNING).
    """
    TRACE    = 5
    DEBUG    = 10
    INFO     = 20
    WARNING  = 30
    ERROR    = 40
    CRITICAL = 50

    def __str__(self) -> str:
        return self.name
