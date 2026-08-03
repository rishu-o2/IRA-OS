from dataclasses import dataclass
from typing import Type, Any, Optional, Callable
from .lifetime import Lifetime

@dataclass
class ServiceDescriptor:
    """
    Describes a service registered in the Dependency Injection Container.
    """
    interface: Type
    lifetime: Lifetime
    implementation: Optional[Type] = None
    instance: Optional[Any] = None
    factory: Optional[Callable] = None

    def __post_init__(self):
        # A descriptor must have exactly one way to provide the service
        provided_ways = sum(
            1 for x in (self.implementation, self.instance, self.factory) if x is not None
        )
        if provided_ways != 1:
            raise ValueError(
                f"ServiceDescriptor for {self.interface} must provide exactly one of: "
                "implementation, instance, or factory."
            )
