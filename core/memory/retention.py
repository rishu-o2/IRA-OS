from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Iterable

from .models import MemoryRecord


class RetentionPolicy(ABC):
    """Base abstraction for retention policies."""

    @abstractmethod
    def select_candidates(self, records: Iterable[MemoryRecord]) -> list[str]:
        """Return the list of record ids that should be forgotten."""

    def should_forget(self, record: MemoryRecord) -> bool:
        """Evaluate a single record against the policy."""
        return record.id in self.select_candidates([record])


class NeverForget(RetentionPolicy):
    """A retention policy that never forgets anything."""

    def select_candidates(self, records: Iterable[MemoryRecord]) -> list[str]:
        return []


class TTL(RetentionPolicy):
    """Forget memories that have not been updated within the TTL window."""

    def __init__(self, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            raise ValueError("TTL must be greater than zero.")
        self.ttl_seconds = ttl_seconds

    def select_candidates(self, records: Iterable[MemoryRecord]) -> list[str]:
        now = datetime.now(timezone.utc)
        return [
            record.id
            for record in records
            if (now - record.updated_at).total_seconds() > self.ttl_seconds
        ]


class LeastRecentlyUsed(RetentionPolicy):
    """Forget the oldest memories by last accessed order when capacity is exceeded."""

    def __init__(self, max_records: int) -> None:
        if max_records < 0:
            raise ValueError("max_records must be non-negative.")
        self.max_records = max_records

    def select_candidates(self, records: Iterable[MemoryRecord]) -> list[str]:
        records = list(records)
        overflow = len(records) - self.max_records
        if overflow <= 0:
            return []
        sorted_records = sorted(records, key=lambda record: record.last_accessed)
        return [record.id for record in sorted_records[:overflow]]


class ImportanceThreshold(RetentionPolicy):
    """Forget memories with importance below a threshold."""

    def __init__(self, threshold: int) -> None:
        self.threshold = threshold

    def select_candidates(self, records: Iterable[MemoryRecord]) -> list[str]:
        return [record.id for record in records if record.importance < self.threshold]


class RetentionManager:
    """Coordinate retention policy evaluation."""

    def __init__(self, policy: RetentionPolicy) -> None:
        self._policy = policy

    def forget(self, record: MemoryRecord) -> bool:
        return self._policy.should_forget(record)

    def cleanup(self, records: Iterable[MemoryRecord]) -> list[str]:
        return self._policy.select_candidates(records)

    def expire(self, records: Iterable[MemoryRecord]) -> list[str]:
        return self.cleanup(records)
