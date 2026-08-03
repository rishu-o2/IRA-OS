from enum import Enum, auto

class Permission(Enum):
    READ_MEMORY = auto()
    WRITE_MEMORY = auto()
    OPEN_APPLICATION = auto()
    CONTROL_DEVICE = auto()
    SEND_MESSAGE = auto()
    MAKE_CALL = auto()
    READ_FILES = auto()
    WRITE_FILES = auto()
    VOICE_OUTPUT = auto()
    MICROPHONE = auto()
    CAMERA = auto()
    LOCATION = auto()
    PAYMENTS = auto()
    NETWORK = auto()
    SYSTEM = auto()
