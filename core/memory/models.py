import json
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence

from .exceptions import MemoryValidationError


def _normalize_tags(tags: Iterable[str]) -> tuple[str, ...]:
    if tags is None:
        return ()
    if isinstance(tags, str):
        raise MemoryValidationError("Tags must be an iterable of strings, not a single string.")
    normalized = tuple(str(tag) for tag in tags)
    return normalized


def _normalize_metadata(metadata: Mapping[str, Any]) -> Mapping[str, Any]:
    if metadata is None:
        return MappingProxyType({})
    if not isinstance(metadata, Mapping):
        raise MemoryValidationError("Metadata must be a mapping.")
    return MappingProxyType(dict(metadata))


def _validate_json_serializable(value: Any) -> None:
    try:
        json.dumps(value)
    except (TypeError, ValueError) as exc:
        raise MemoryValidationError(
            "MemoryRecord content must be JSON-serializable."
        ) from exc


@dataclass(frozen=True)
class MemoryRecord:
    id: str
    owner_id: str
    namespace: str = "default"
    title: str = ""
    content: Any = None
    metadata: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))
    tags: tuple[str, ...] = field(default_factory=tuple)
    importance: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    access_count: int = 0

    def __post_init__(self) -> None:
        if not self.id:
            raise MemoryValidationError("MemoryRecord.id must not be empty.")
        if not self.owner_id:
            raise MemoryValidationError("MemoryRecord.owner_id must not be empty.")
        if not isinstance(self.namespace, str) or not self.namespace:
            raise MemoryValidationError("MemoryRecord.namespace must be a non-empty string.")
        if not isinstance(self.title, str):
            raise MemoryValidationError("MemoryRecord.title must be a string.")

        object.__setattr__(self, "metadata", _normalize_metadata(self.metadata))
        object.__setattr__(self, "tags", _normalize_tags(self.tags))
        _validate_json_serializable(self.content)

    def with_access(self) -> "MemoryRecord":
        now = datetime.now(timezone.utc)
        return replace(
            self,
            last_accessed=now,
            access_count=self.access_count + 1,
        )

    def with_update(self, **kwargs: Any) -> "MemoryRecord":
        now = datetime.now(timezone.utc)
        updated = replace(self, **kwargs)
        return replace(updated, updated_at=now)


@dataclass(frozen=True)
class SearchQuery:
    text: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)
    namespace: str | None = None
    limit: int = 10

    def __post_init__(self) -> None:
        if self.limit <= 0:
            raise MemoryValidationError("SearchQuery.limit must be greater than zero.")
        if self.tags is None:
            object.__setattr__(self, "tags", ())
        elif isinstance(self.tags, str):
            raise MemoryValidationError("SearchQuery.tags must be an iterable of strings.")


@dataclass(frozen=True)
class SearchResult:
    record: MemoryRecord
    score: float


@dataclass(frozen=True)
class MemoryStats:
    total_records: int
    namespaces: int
    tag_count: int
