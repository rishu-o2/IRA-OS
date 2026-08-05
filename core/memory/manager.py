import asyncio
from datetime import datetime, timezone
from typing import Any, List, Optional

from core.events import EventBus
from core.lifecycle.interfaces import LifecycleComponent
from core.logging import Logger

from .events import (
    MemoryStored,
    MemoryUpdated,
    MemoryDeleted,
    MemoryAccessed,
    MemoryForgotten,
)
from .indexes import MemoryIndex
from .models import MemoryRecord, SearchQuery, SearchResult, MemoryStats
from .retention import RetentionManager
from .search import SearchEngine
from .store import MemoryStore


class MemoryManager(LifecycleComponent):
    """Facade for memory storage, retrieval, search, and retention."""

    def __init__(
        self,
        store: MemoryStore,
        search_engine: SearchEngine,
        retention_manager: RetentionManager,
        logger: Logger,
        event_bus: Optional[EventBus] = None,
    ):
        self._store = store
        self._search_engine = search_engine
        self._retention_manager = retention_manager
        self._logger = logger
        self._event_bus = event_bus
        self._lock = asyncio.Lock()

    # --- Lifecycle Hooks ---

    async def start(self) -> None:
        self._logger.info("MemoryManager starting.")

    async def shutdown(self) -> None:
        self._logger.info("MemoryManager shutting down.")
        self._store.clear()

    # --- Public Memory API ---

    async def remember(self, record: MemoryRecord) -> None:
        async with self._lock:
            self._store.add(record)
            self._logger.debug(f"Stored memory {record.id} in namespace '{record.namespace}'.")
            if self._event_bus:
                await self._event_bus.publish(
                    MemoryStored(
                        payload={
                            "memory_id": record.id,
                            "owner_id": record.owner_id,
                            "namespace": record.namespace,
                        },
                        source="MemoryManager",
                        memory_id=record.id,
                        owner_id=record.owner_id,
                        namespace=record.namespace,
                    )
                )

    async def recall(self, memory_id: str) -> MemoryRecord:
        async with self._lock:
            record = self._store.get(memory_id)
            updated = record.with_access()
            self._store.replace(updated)
            self._logger.debug(f"Accessed memory {memory_id}.")
            if self._event_bus:
                await self._event_bus.publish(
                    MemoryAccessed(
                        payload={
                            "memory_id": memory_id,
                            "owner_id": record.owner_id,
                            "namespace": record.namespace,
                        },
                        source="MemoryManager",
                        memory_id=memory_id,
                        owner_id=record.owner_id,
                        namespace=record.namespace,
                    )
                )
            return updated

    async def search(self, query: SearchQuery) -> List[SearchResult]:
        async with self._lock:
            return self._search_engine.search(query)

    async def forget(self, memory_id: str) -> None:
        async with self._lock:
            record = self._store.get(memory_id)
            self._store.delete(memory_id)
            self._logger.debug(f"Forgot memory {memory_id}.")
            if self._event_bus:
                await self._event_bus.publish(
                    MemoryForgotten(
                        payload={
                            "memory_id": memory_id,
                            "owner_id": record.owner_id,
                            "namespace": record.namespace,
                        },
                        source="MemoryManager",
                        memory_id=memory_id,
                        owner_id=record.owner_id,
                        namespace=record.namespace,
                    )
                )

    async def delete(self, memory_id: str) -> None:
        async with self._lock:
            record = self._store.get(memory_id)
            self._store.delete(memory_id)
            self._logger.debug(f"Deleted memory {memory_id}.")
            if self._event_bus:
                await self._event_bus.publish(
                    MemoryDeleted(
                        payload={
                            "memory_id": memory_id,
                            "owner_id": record.owner_id,
                            "namespace": record.namespace,
                        },
                        source="MemoryManager",
                        memory_id=memory_id,
                        owner_id=record.owner_id,
                        namespace=record.namespace,
                    )
                )

    async def update(self, memory_id: str, **fields) -> MemoryRecord:
        async with self._lock:
            updated = self._store.update(memory_id, **fields)
            self._logger.debug(f"Updated memory {memory_id}.")
            if self._event_bus:
                await self._event_bus.publish(
                    MemoryUpdated(
                        payload={
                            "memory_id": memory_id,
                            "owner_id": updated.owner_id,
                            "namespace": updated.namespace,
                        },
                        source="MemoryManager",
                        memory_id=updated.id,
                        owner_id=updated.owner_id,
                        namespace=updated.namespace,
                    )
                )
            return updated

    async def replace(self, record: MemoryRecord) -> None:
        async with self._lock:
            self._store.replace(record)
            self._logger.debug(f"Replaced memory {record.id}.")
            if self._event_bus:
                await self._event_bus.publish(
                    MemoryUpdated(
                        payload={
                            "memory_id": record.id,
                            "owner_id": record.owner_id,
                            "namespace": record.namespace,
                        },
                        source="MemoryManager",
                        memory_id=record.id,
                        owner_id=record.owner_id,
                        namespace=record.namespace,
                    )
                )

    async def list(self, namespace: str | None = None, owner_id: str | None = None) -> list[MemoryRecord]:
        async with self._lock:
            return self._store.list(namespace=namespace, owner_id=owner_id)

    async def stats(self) -> MemoryStats:
        async with self._lock:
            return self._store.stats()

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()

    async def cleanup(self) -> None:
        async with self._lock:
            candidates = self._retention_manager.cleanup(self._store.list())

        for memory_id in candidates:
            await self.forget(memory_id)

    async def expire(self) -> None:
        async with self._lock:
            candidates = self._retention_manager.expire(self._store.list())

        for memory_id in candidates:
            await self.forget(memory_id)
