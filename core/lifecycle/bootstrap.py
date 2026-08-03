from .manager import LifecycleManager
from core.config import ConfigurationManager
from core.logging import LoggerFactory, LoggingModule
from core.container import Container
from core.events import EventBus


class Bootstrap:
    """
    Kernel Bootstrapper for IRA OS.
    Assembles the kernel components (Config, Logging, DI Container, Event Bus)
    and registers them with a new LifecycleManager.
    Does NOT manage the event loop or start the application.
    """
    
    @staticmethod
    def build() -> LifecycleManager:
        """
        Constructs and wires the kernel, returning a populated LifecycleManager.
        """
        # 1. Initialize Configuration
        config_manager = ConfigurationManager()
        # Default config load, this would ideally read from standard places
        config_manager.load()
        config = config_manager.get()
        
        # 2. Initialize Logging
        log_factory = LoggerFactory(
            level=config.logging.level,
            # Simple fallback defaults for kernel boot
        )
        
        # 3. Initialize DI Container
        container = Container()
        container.install(LoggingModule(log_factory))
        
        # 4. Initialize Event Bus
        event_bus = EventBus()
        container.register_instance(EventBus, event_bus)
        
        # 5. Initialize Lifecycle Manager
        lifecycle_manager = LifecycleManager()
        
        # Register Kernel Components
        lifecycle_manager.register(
            name="Configuration",
            instance=config_manager,
            priority=10
        )
        
        lifecycle_manager.register(
            name="Logging",
            instance=log_factory,
            dependencies=["Configuration"],
            priority=20
        )
        
        lifecycle_manager.register(
            name="Container",
            instance=container,
            dependencies=["Logging"],
            priority=30
        )
        
        lifecycle_manager.register(
            name="EventBus",
            instance=event_bus,
            dependencies=["Container"],
            priority=40
        )
        
        return lifecycle_manager
