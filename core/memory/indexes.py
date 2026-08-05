import threading
from collections import defaultdict
from typing import Iterable

from .models import MemoryRecord


class MemoryIndex:
    """In-memory indexes to support fast lookup by id, namespace, tag, and owner."""

    def __init__(self) -> None:
        self._by_id: dict[str, MemoryRecord] = {}
        self._by_namespace: dict[str, set[str]] = defaultdict(set)
        self._by_tags: dict[str, set[str]] = defaultdict(set)
        self._by_owner: dict[str, set[str]] = defaultdict(set)
        self._lock = threading.RLock()

    def add(self, record: MemoryRecord) -> None:
        with self._lock:
            self._by_id[record.id] = record
            self._by_namespace[record.namespace].add(record.id)
            self._by_owner[record.owner_id].add(record.id)
            for tag in record.tags:
                self._by_tags[tag].add(record.id)

    def update(self, old_record: MemoryRecord, new_record: MemoryRecord) -> None:
        with self._lock:
            self.remove(old_record.id)
            self.add(new_record)

    def remove(self, record_id: str) -> None:
        with self._lock:
            record = self._by_id.pop(record_id, None)
            if not record:
                return

            self._by_namespace[record.namespace].discard(record_id)
            if not self._by_namespace[record.namespace]:
                self._by_namespace.pop(record.namespace, None)

            self._by_owner[record.owner_id].discard(record_id)
            if not self._by_owner[record.owner_id]:
                self._by_owner.pop(record.owner_id, None)

            for tag in record.tags:
                self._by_tags[tag].discard(record_id)
                if not self._by_tags[tag]:
                    self._by_tags.pop(tag, None)

    def get_by_namespace(self, namespace: str) -> set[str]:
        with self._lock:
            return set(self._by_namespace.get(namespace, set()))

    def get_by_owner(self, owner_id: str) -> set[str]:
        with self._lock:
            return set(self._by_owner.get(owner_id, set()))

    def get_by_tag(self, tag: str) -> set[str]:
        with self._lock:
            return set(self._by_tags.get(tag, set()))

    def all_ids(self) -> set[str]:
        with self._lock:
            return set(self._by_id.keys())

    def namespace_count(self) -> int:
        with self._lock:
            return len(self._by_namespace)

    def tag_count(self) -> int:
        with self._lock:
            return len(self._by_tags)
