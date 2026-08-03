from typing import Any

class SecretValue:
    """
    Wrapper for sensitive configuration values.
    Prevents accidental logging by overriding string representations.
    """
    def __init__(self, value: str):
        self._value = value

    def get_secret_value(self) -> str:
        """Explicitly retrieve the actual secret value."""
        return self._value

    def __repr__(self) -> str:
        return "SecretValue(******)"

    def __str__(self) -> str:
        return "******"
        
    def __eq__(self, other: Any) -> bool:
        if isinstance(other, SecretValue):
            return self._value == other._value
        return False
        
    def __hash__(self) -> int:
        return hash(self._value)
