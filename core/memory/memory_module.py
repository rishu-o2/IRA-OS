from core.container import Lifetime, Module, ContainerProtocol
from core.logging import LoggerFactory, Logger
from core.events import EventBus

from .indexes import MemoryIndex
from .store import MemoryStore
from .search import SearchEngine
from .retention import RetentionManager, NeverForget
from .manager import MemoryManager


class MemoryModule(Module):
    """DI module for the Memory Engine."""

    def __init__(self, retention_policy: RetentionManager | None = None):
        self._retention_manager = retention_policy or RetentionManager(NeverForget())

    def configure(self, container: ContainerProtocol) -> None:
        container.register_singleton(MemoryIndex)
        container.register_singleton(MemoryStore)
        container.register_singleton(SearchEngine)
        container.register_instance(RetentionManager, self._retention_manager)

        async def build_memory_manager() -> MemoryManager:
            store = await container.resolve(MemoryStore)
            search_engine = await container.resolve(SearchEngine)
            retention_manager = await container.resolve(RetentionManager)
            logger_factory = await container.resolve(LoggerFactory)
            logger = logger_factory.get("core.memory")

            event_bus = None
            if container.has(EventBus):
                event_bus = await container.resolve(EventBus)

            return MemoryManager(store, search_engine, retention_manager, logger, event_bus)

        container.register_factory(MemoryManager, factory=build_memory_manager, lifetime=Lifetime.SINGLETON)
