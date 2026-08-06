from typing import List

from .contracts import PluginLoader
from .models import PluginManifest, PluginMetadata, PluginType


class DefaultPluginLoader(PluginLoader):
    """
    Scaffold implementation of PluginLoader.
    No filesystem scanning or dynamic imports.
    """
    def __init__(self) -> None:
        pass

    def discover(self) -> List[PluginMetadata]:
        # Scaffold: Return a mock built-in plugin for testing purposes
        manifest = PluginManifest(
            id="core.example.plugin",
            name="Example Plugin",
            version="1.0.0",
            author="IRA OS",
            description="A built-in example plugin",
            type=PluginType.BUILTIN,
            dependencies=[],
            capabilities=[],
            minimum_os_version="1.0.0",
            api_version="1.0"
        )
        metadata = PluginMetadata(
            manifest=manifest,
            source_path="builtin://core.example.plugin",
            checksum="00000000"
        )
        return [metadata]
