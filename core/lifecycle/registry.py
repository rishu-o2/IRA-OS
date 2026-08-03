from typing import Dict, List, Optional
from .models import ComponentRegistration
from .exceptions import RegistrationError


class ComponentRegistry:
    """
    Manages the registration of all lifecycle components.
    Does not execute lifecycle events, only maintains the registry.
    """
    def __init__(self):
        self._components: Dict[str, ComponentRegistration] = {}

    def register(self, registration: ComponentRegistration) -> None:
        """Register a new component. Raises RegistrationError if duplicate name."""
        if registration.name in self._components:
            raise RegistrationError(f"Component '{registration.name}' is already registered.")
        
        self._components[registration.name] = registration

    def remove(self, name: str) -> None:
        """Remove a component from the registry."""
        self._components.pop(name, None)

    def replace(self, name: str, registration: ComponentRegistration) -> None:
        """Replace an existing component with a new registration."""
        if name != registration.name:
            raise RegistrationError("Name mismatch when replacing component registration.")
        self._components[name] = registration
        
    def update(self, name: str, **kwargs) -> None:
        """Update metadata of an existing registration without replacing the instance."""
        if name not in self._components:
            raise RegistrationError(f"Component '{name}' not found for update.")
            
        current = self._components[name]
        
        # Valid fields that can be updated
        allowed_fields = {"dependencies", "priority", "enabled", "critical", "startup_timeout", "shutdown_timeout"}
        for k in kwargs:
            if k not in allowed_fields:
                raise RegistrationError(f"Cannot update field '{k}' on ComponentRegistration.")
        
        updated_kwargs = {
            "name": current.name,
            "instance": current.instance,
            "dependencies": kwargs.get("dependencies", current.dependencies),
            "priority": kwargs.get("priority", current.priority),
            "enabled": kwargs.get("enabled", current.enabled),
            "critical": kwargs.get("critical", current.critical),
            "startup_timeout": kwargs.get("startup_timeout", current.startup_timeout),
            "shutdown_timeout": kwargs.get("shutdown_timeout", current.shutdown_timeout)
        }
        
        self._components[name] = ComponentRegistration(**updated_kwargs)

    def get(self, name: str) -> Optional[ComponentRegistration]:
        """Get a component registration by name."""
        return self._components.get(name)

    def get_all(self) -> List[ComponentRegistration]:
        """Get all registered components."""
        return list(self._components.values())

    def contains(self, name: str) -> bool:
        """Check if a component is registered."""
        return name in self._components
