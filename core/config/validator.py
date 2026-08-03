import dataclasses
from typing import Any, Type, get_origin, get_args, Union
from types import UnionType
from .exceptions import ValidationError
from .secrets import SecretValue

class Validator:
    """
    Validates a raw dictionary against a dataclass schema.
    Performs type coercion (especially from EnvVar strings).
    Applies strict domain rules (e.g. port limits, timeouts).
    """
    
    @classmethod
    def validate_and_build(cls, schema: Type[Any], raw_data: dict[str, Any], path: str = "") -> Any:
        if not dataclasses.is_dataclass(schema):
            raise ValidationError(f"Schema {schema.__name__} must be a dataclass.")

        kwargs = {}
        for field in dataclasses.fields(schema):
            field_name = field.name
            field_path = f"{path}.{field_name}" if path else field_name
            
            value = raw_data.get(field_name, dataclasses.MISSING)
            
            if value is dataclasses.MISSING:
                if field.default is not dataclasses.MISSING:
                    kwargs[field_name] = field.default
                    continue
                elif field.default_factory is not dataclasses.MISSING:
                    kwargs[field_name] = field.default_factory()
                    continue
                else:
                    raise ValidationError(f"Missing required configuration section/field: '{field_path}'")
            
            # Recursively build nested dataclasses
            if dataclasses.is_dataclass(field.type):
                if not isinstance(value, dict):
                    raise ValidationError(f"Expected dictionary for '{field_path}', got {type(value).__name__}")
                kwargs[field_name] = cls.validate_and_build(field.type, value, field_path)
            else:
                kwargs[field_name] = cls._coerce_and_validate(value, field.type, field_path)
                
        # Instance validation rules
        instance = schema(**kwargs)
        cls._apply_rules(instance)
        return instance
        
    @classmethod
    def _coerce_and_validate(cls, value: Any, expected_type: Any, path: str) -> Any:
        # Handle Union (e.g., SecretValue | None, SecretValue | str)
        origin = get_origin(expected_type)
        if origin is Union or origin is UnionType:
            args = get_args(expected_type)
            # Try to match a type in the union
            if value is None and type(None) in args:
                return None
            
            # Special case for SecretValue | None or SecretValue | str
            if SecretValue in args:
                if value is None:
                    return None
                return SecretValue(str(value))
                
            # Naive union matching (first match wins)
            for t in args:
                if t is type(None): continue
                try:
                    return cls._coerce(value, t)
                except Exception:
                    continue
            raise ValidationError(f"Type mismatch at '{path}': expected {expected_type}, got {type(value).__name__}")

        # If it's a specific type
        if expected_type is SecretValue:
            if value is None:
                raise ValidationError(f"Secret cannot be None at '{path}'")
            return SecretValue(str(value))
            
        if expected_type is bool and isinstance(value, str):
            val_lower = value.lower()
            if val_lower in ("true", "1", "yes", "on"): return True
            if val_lower in ("false", "0", "no", "off"): return False
            raise ValidationError(f"Invalid boolean string '{value}' at '{path}'")

        try:
            return cls._coerce(value, expected_type)
        except Exception as e:
            raise ValidationError(f"Type mismatch at '{path}': expected {expected_type}, got {type(value).__name__}. {e}")

    @classmethod
    def _coerce(cls, value: Any, expected_type: Any) -> Any:
        # Simple list support
        if get_origin(expected_type) is list:
            if not isinstance(value, list):
                if isinstance(value, str):
                    # Coerce comma separated string to list
                    return [x.strip() for x in value.split(",")]
                raise ValueError("Not a list")
            item_type = get_args(expected_type)[0] if get_args(expected_type) else str
            return [cls._coerce(v, item_type) for v in value]

        if expected_type in (int, float, str, bool):
            return expected_type(value)
            
        return value

    @classmethod
    def _apply_rules(cls, instance: Any) -> None:
        """Domain specific rules based on the section class."""
        class_name = instance.__class__.__name__
        
        if class_name == "ServerConfig":
            if not (1 <= getattr(instance, "port") <= 65535):
                raise ValidationError(f"Port must be between 1 and 65535, got {getattr(instance, 'port')}")
            if getattr(instance, "timeout") < 0:
                raise ValidationError(f"Timeout must be >= 0, got {getattr(instance, 'timeout')}")
        elif class_name == "KernelConfig":
            if getattr(instance, "event_limit") <= 0:
                raise ValidationError(f"Event limit must be positive, got {getattr(instance, 'event_limit')}")
