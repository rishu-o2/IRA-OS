from enum import Enum


class ComponentState(Enum):
    """
    Represents the current state of a component in its lifecycle.
    """
    CREATED = "CREATED"
    BOOTING = "BOOTING"
    BOOTED = "BOOTED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    SHUTTING_DOWN = "SHUTTING_DOWN"
    FAILED = "FAILED"
    RESTARTING = "RESTARTING"
