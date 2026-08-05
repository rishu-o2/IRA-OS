import threading
from typing import Iterable
from .exceptions import DuplicateMemory, MemoryNotFound
from .indexes import MemoryIndex
from .models import MemoryRecord, MemoryStats


class MemoryStore:
    """In-memory storage layer for MemoryRecord objects."""

    def __init__(self, index: MemoryIndex) -> None:
        self._index = index
        self._lock = threading.RLock()

    def add(self, record: MemoryRecord) -> None:
        with self._lock:
            if record.id in self._index.all_ids():
                raise DuplicateMemory(f"Memory record with id '{record.id}' already exists.")
            self._index.add(record)

    def update(self, record_id: str, **fields) -> MemoryRecord:
        with self._lock:
            current = self.get(record_id)
            updated = current.with_update(**fields)
            self._index.update(current, updated)
            return updated

    def replace(self, record: MemoryRecord) -> None:
        with self._lock:
            if record.id not in self._index.all_ids():
                raise MemoryNotFound(f"Memory record with id '{record.id}' does not exist.")
            existing = self.get(record.id)
            self._index.update(existing, record)

    def delete(self, record_id: str) -> None:
        with self._lock:
            if record_id not in self._index.all_ids():
                raise MemoryNotFound(f"Memory record with id '{record_id}' does not exist.")
            self._index.remove(record_id)

    def exists(self, record_id: str) -> bool:
        with self._lock:
            return record_id in self._index.all_ids()

    def get(self, record_id: str) -> MemoryRecord:
        with self._lock:
            if record_id not in self._index.all_ids():
                raise MemoryNotFound(f"Memory record with id '{record_id}' does not exist.")
            # Direct access from the index rather than copying
            return self._index._by_id[record_id]

    def list(self, namespace: str | None = None, owner_id: str | None = None) -> list[MemoryRecord]:
        with self._lock:
            ids = set(self._index.all_ids())
            if namespace is not None:
                ids &= self._index.get_by_namespace(namespace)
            if owner_id is not None:
                ids &= self._index.get_by_owner(owner_id)
            return [self._index._by_id[memory_id] for memory_id in ids]

    def clear(self) -> None:
        with self._lock:
            for record_id in list(self._index.all_ids()):
                self._index.remove(record_id)

    def stats(self) -> MemoryStats:
        with self._lock:
            return MemoryStats(
                total_records=len(self._index.all_ids()),
                namespaces=self._index.namespace_count(),
                tag_count=self._index.tag_count(),
            )
