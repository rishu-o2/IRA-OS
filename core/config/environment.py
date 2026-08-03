import os
from enum import Enum, auto

class Environment(Enum):
    DEVELOPMENT = auto()
    TESTING = auto()
    PRODUCTION = auto()

    @classmethod
    def current(cls) -> 'Environment':
        """Get the current environment from IRA_ENV, defaulting to DEVELOPMENT."""
        env_str = os.environ.get("IRA_ENV", "development").lower()
        if env_str == "production":
            return cls.PRODUCTION
        elif env_str == "testing" or env_str == "test":
            return cls.TESTING
        return cls.DEVELOPMENT

    @classmethod
    def is_development(cls) -> bool:
        return cls.current() == cls.DEVELOPMENT

    @classmethod
    def is_testing(cls) -> bool:
        return cls.current() == cls.TESTING

    @classmethod
    def is_production(cls) -> bool:
        return cls.current() == cls.PRODUCTION
