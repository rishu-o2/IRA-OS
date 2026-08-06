from .contracts import PluginValidator
from .exceptions import PluginValidationError
from .models import PluginMetadata


class DefaultPluginValidator(PluginValidator):
    """
    Validates plugin manifests and metadata structures.
    """
    def __init__(self) -> None:
        pass

    def validate(self, metadata: PluginMetadata) -> bool:
        if not metadata:
            raise PluginValidationError("Plugin metadata is missing.")
        
        manifest = metadata.manifest
        if not manifest:
            raise PluginValidationError("Plugin manifest is missing.")
            
        if not manifest.id or not isinstance(manifest.id, str):
            raise PluginValidationError("Plugin ID is required and must be a string.")
            
        if not manifest.version:
            raise PluginValidationError("Plugin version is required.")
            
        # Optional: check ID format, dependency resolution, etc.
        # For Milestone 14, basic presence validation is sufficient.
        
        return True
