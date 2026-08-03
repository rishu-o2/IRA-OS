from typing import Protocol, Any, Dict
import os
import json
from .secrets import SecretValue

class ConfigProvider(Protocol):
    def load(self) -> Dict[str, Any]:
        """Load configuration as a dictionary."""
        ...

class DictProvider:
    """Provides configuration from an in-memory dictionary."""
    def __init__(self, data: Dict[str, Any]):
        self._data = data
        
    def load(self) -> Dict[str, Any]:
        return self._data

class JsonFileProvider:
    """Provides configuration from a JSON file."""
    def __init__(self, filepath: str):
        self.filepath = filepath
        
    def load(self) -> Dict[str, Any]:
        if not os.path.exists(self.filepath):
            return {}
            
        with open(self.filepath, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}

class EnvVarProvider:
    """
    Provides configuration from environment variables.
    Maps variables prefixed with IRA_ to their respective sections.
    Example: IRA_SERVER_PORT=8080 -> {'server': {'port': '8080'}}
    """
    def __init__(self, prefix: str = "IRA_"):
        self.prefix = prefix
        
    def load(self) -> Dict[str, Any]:
        config: Dict[str, Any] = {}
        
        for key, value in os.environ.items():
            if not key.startswith(self.prefix):
                continue
                
            # Strip prefix and split by first underscore only since our schema is 1 level deep.
            # e.g., IRA_SECURITY_API_KEY -> SECURITY_API_KEY -> ['security', 'api_key']
            path = key[len(self.prefix):].lower().split('_', 1)
            
            # Navigate/build nested dictionaries
            current = config
            for part in path[:-1]:
                if part not in current:
                    current[part] = {}
                elif not isinstance(current[part], dict):
                    # If there's a conflict where a parent is not a dict, skip
                    break
                current = current[part]
            else:
                # Assign the final value
                leaf = path[-1]
                
                # Check if it should be wrapped as a SecretValue.
                # In EnvVarProvider, we can heuristically wrap keys containing 'key', 'secret', 'token', 'password'
                # But it's better to let Validator convert strings to SecretValue when mapping to schema!
                # We'll just return the raw string here, and Validator will coerce it based on type hints.
                current[leaf] = value
                
        return config
