from enum import Enum, auto

class Role(Enum):
    OWNER = auto()
    ADMIN = auto()
    ASSISTANT = auto()
    GUEST = auto()
    AUTOMATION = auto()
    DEVELOPER = auto()
