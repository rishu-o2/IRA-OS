import os
import tempfile
import json
import asyncio
from contextlib import contextmanager
from core.config import (
    ConfigurationManager, ConfigModule, Environment, SecretValue,
    ValidationError, ServerConfig, LLMConfig
)
from core.container import Container

@contextmanager
def assert_raises(exc_type, match=None):
    try:
        yield
    except exc_type as e:
        if match and match not in str(e):
            raise AssertionError(f"Expected exception message to match '{match}', got '{e}'")
        pass
    except Exception as e:
        raise AssertionError(f"Expected {exc_type.__name__}, but got {type(e).__name__}")
    else:
        raise AssertionError(f"Expected {exc_type.__name__}, but no exception was raised")

@contextmanager
def env_var_cleaner_mgr():
    """Context manager to ensure environment variables are cleaned up."""
    original = dict(os.environ)
    try:
        yield
    finally:
        os.environ.clear()
        os.environ.update(original)

def test_environment_selection():
    with env_var_cleaner_mgr():
        os.environ["IRA_ENV"] = "production"
        assert Environment.is_production() is True
        assert Environment.is_development() is False
        
        os.environ["IRA_ENV"] = "testing"
        assert Environment.is_testing() is True

def test_secret_value():
    secret = SecretValue("super-secret")
    assert str(secret) == "******"
    assert repr(secret) == "SecretValue(******)"
    assert secret.get_secret_value() == "super-secret"
    
    secret2 = SecretValue("super-secret")
    assert secret == secret2

def test_provider_priority_and_deep_merge():
    with env_var_cleaner_mgr():
        manager = ConfigurationManager()
        
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as f:
            json.dump({"server": {"port": 9000, "host": "0.0.0.0"}, "desktop": {"theme": "light"}}, f)
            json_path = f.name
            
        try:
            os.environ["IRA_SERVER_PORT"] = "9999"
            manager.override({"server": {"timeout": 10.0}})
            
            config = manager.load(json_path)
            
            assert config.server.port == 9999
            assert config.server.host == "0.0.0.0"
            assert config.server.timeout == 10.0
            
            assert config.logging.level == "INFO"
            assert config.desktop.theme == "light"
            
        finally:
            os.remove(json_path)

def test_validation_rules():
    with env_var_cleaner_mgr():
        manager = ConfigurationManager()
        
        manager.override({"server": {"port": 70000}})
        with assert_raises(ValidationError, match="Port must be between 1 and 65535"):
            manager.load("non_existent.json")
            
        manager = ConfigurationManager()
        manager.override({"server": {"timeout": -5.0}})
        with assert_raises(ValidationError, match="Timeout must be >= 0"):
            manager.load("non_existent.json")

def test_validation_type_coercion():
    with env_var_cleaner_mgr():
        manager = ConfigurationManager()
        
        os.environ["IRA_SERVER_PORT"] = "5000"
        os.environ["IRA_SERVER_TIMEOUT"] = "5.5"
        os.environ["IRA_PLUGIN_ENABLED"] = "true"
        
        config = manager.load("non_existent.json")
        
        assert config.server.port == 5000
        assert isinstance(config.server.port, int)
        
        assert config.server.timeout == 5.5
        assert isinstance(config.server.timeout, float)
        
        assert config.plugin.enabled is True

def test_secret_resolution():
    with env_var_cleaner_mgr():
        manager = ConfigurationManager()
        
        os.environ["IRA_SECURITY_API_KEY"] = "my-api-key"
        os.environ["IRA_LLM_PROVIDER_KEY"] = "openai-key"
        os.environ["IRA_DATABASE_CONNECTION_STRING"] = "postgres://usr:pwd@host/db"
        
        config = manager.load("non_existent.json")
        
        assert isinstance(config.security.api_key, SecretValue)
        assert config.security.api_key.get_secret_value() == "my-api-key"
        
        assert isinstance(config.llm.provider_key, SecretValue)
        assert config.llm.provider_key.get_secret_value() == "openai-key"
        
        assert isinstance(config.database.connection_string, SecretValue)
        assert config.database.connection_string.get_secret_value() == "postgres://usr:pwd@host/db"

def test_missing_section_fails():
    manager = ConfigurationManager()
    old_default = manager.get_default_dict
    
    def bad_defaults():
        d = old_default()
        del d["server"]
        return d
        
    manager.get_default_dict = bad_defaults
    
    with assert_raises(ValidationError, match="Missing required configuration section/field: 'server'"):
        manager.load("non_existent.json")

def test_di_integration():
    manager = ConfigurationManager()
    manager.override({"server": {"port": 1234}})
    
    container = Container()
    container.install(ConfigModule(manager))
    
    class MyServer:
        def __init__(self, config: ServerConfig):
            self.config = config
            
    class MyLLM:
        def __init__(self, config: LLMConfig):
            self.config = config
            
    container.register_transient(MyServer)
    container.register_transient(MyLLM)
    
    async def run_test():
        srv = await container.resolve(MyServer)
        llm = await container.resolve(MyLLM)
        
        assert srv.config.port == 1234
        assert llm.config.model == "gpt-4o"  # Default
        
    asyncio.run(run_test())

def test_section_retrieval():
    manager = ConfigurationManager()
    manager.load("non_existent.json")
    
    server_config = manager.section(ServerConfig)
    assert isinstance(server_config, ServerConfig)
    
    with assert_raises(ValueError):
        manager.section(SecretValue)
