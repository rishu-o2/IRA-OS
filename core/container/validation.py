import inspect
from typing import Dict, Type, Set, List
from .registration import ServiceDescriptor
from .exceptions import ValidationError

class Validator:
    """
    Validates the Dependency Injection container graph without instantiating objects.
    Detects missing registrations and circular dependencies.
    """
    def __init__(self, registry: Dict[Type, ServiceDescriptor]):
        self._registry = registry

    def validate(self) -> List[str]:
        """
        Runs validation across all registered services.
        Returns a list of error messages. Empty list means the graph is valid.
        """
        errors = []
        
        for interface in self._registry.keys():
            try:
                self._validate_node(interface, set())
            except Exception as e:
                errors.append(str(e))
                
        return errors

    def _validate_node(self, interface: Type, resolution_chain: Set[Type]) -> None:
        interface_name = getattr(interface, '__name__', str(interface))
        
        if interface in resolution_chain:
            chain_str = " -> ".join([getattr(t, '__name__', str(t)) for t in resolution_chain]) + f" -> {interface_name}"
            raise ValidationError(f"Circular dependency detected: {chain_str}")

        if interface not in self._registry:
            raise ValidationError(f"Missing dependency: No registration found for {interface_name}")

        descriptor = self._registry[interface]

        if descriptor.instance is not None:
            return  # Instances have no dependencies to resolve

        target = descriptor.factory if descriptor.factory else descriptor.implementation
        if target is None:
            raise ValidationError(f"ServiceDescriptor for {interface.__name__} lacks implementation or factory.")

        new_resolution_chain = resolution_chain | {interface}
        sig = inspect.signature(target)
        try:
            from typing import get_type_hints
            import sys
            hint_target = target.__init__ if isinstance(target, type) else target
            globalns = sys.modules[target.__module__].__dict__ if hasattr(target, '__module__') and target.__module__ in sys.modules else {}
            type_hints = get_type_hints(hint_target, globalns=globalns)
        except Exception:
            type_hints = {}

        for name, param in sig.parameters.items():
            if name == 'self':
                continue
                
            param_type = type_hints.get(name, param.annotation)
            
            if param_type == inspect.Parameter.empty:
                raise ValidationError(f"Parameter '{name}' in {target.__name__} lacks type annotation.")
                
            # Check if it has a default value. If it does, and it's not registered, we can skip validating its deep graph
            # because it will fall back to default at runtime.
            if param_type not in self._registry and param.default != inspect.Parameter.empty:
                continue
                
            try:
                self._validate_node(param_type, new_resolution_chain)
            except ValidationError as e:
                if "Circular dependency detected" in str(e):
                    raise
                if param.default != inspect.Parameter.empty:
                    continue
                raise ValidationError(f"Cannot resolve parameter '{name}' of type {param_type} for {target.__name__}. Cause: {e}")
