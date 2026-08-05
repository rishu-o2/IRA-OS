import asyncio
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass

import pytest

from core.container import Container
from core.events import EventBus, Event
from core.logging import LoggerFactory
from core.logging.sinks import NullSink
from core.memory import (
    MemoryModule,
    MemoryManager,
    MemoryRecord,
    SearchQuery,
    MemoryStats,
    MemoryIndex,
    MemoryStore,
    SearchEngine,
    RetentionManager,
    NeverForget,
    TTL,
    LeastRecentlyUsed,
    ImportanceThreshold,
    MemoryStored,
    MemoryUpdated,
    MemoryDeleted,
    MemoryAccessed,
    MemoryForgotten,
)


@pytest.fixture
def logger_factory() -> LoggerFactory:
    return LoggerFactory(sinks=[NullSink()])


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture
async def memory_manager(logger_factory: LoggerFactory, event_bus: EventBus) -> MemoryManager:
    container = Container()
    container.register_instance(LoggerFactory, logger_factory)
    container.register_instance(EventBus, event_bus)
    container.install(MemoryModule())
    return await container.resolve(MemoryManager)


def make_record(record_id: str, owner_id: str = "owner", namespace: str = "default") -> MemoryRecord:
    return MemoryRecord(
        id=record_id,
        owner_id=owner_id,
        namespace=namespace,
        title=f"Title {record_id}",
        content={"text": f"content {record_id}"},
        metadata={"source": "tests"},
        tags=("tag1", "tag2"),
        importance=1,
    )


@pytest.mark.anyio
async def test_remember_and_recall(memory_manager: MemoryManager):
    record = make_record("m1")
    await memory_manager.remember(record)

    recalled = await memory_manager.recall("m1")
    assert recalled.id == record.id
    assert recalled.access_count == 1
    assert recalled.last_accessed >= record.last_accessed


@pytest.mark.anyio
async def test_duplicate_memory_raises(memory_manager: MemoryManager):
    record = make_record("m2")
    await memory_manager.remember(record)

    with pytest.raises(Exception):
        await memory_manager.remember(record)


@pytest.mark.anyio
async def test_update_and_replace(memory_manager: MemoryManager):
    record = make_record("m3")
    await memory_manager.remember(record)

    updated = await memory_manager.update("m3", title="Updated Title", importance=5)
    assert updated.title == "Updated Title"
    assert updated.importance == 5

    replacement = MemoryRecord(
        id="m3",
        owner_id="owner",
        namespace="default",
        title="Replaced Title",
        content={"text": "replaced"},
        metadata={"source": "replacement"},
        tags=("tag3",),
        importance=10,
    )
    await memory_manager.replace(replacement)
    replaced = await memory_manager.recall("m3")
    assert replaced.title == "Replaced Title"
    assert "tag3" in replaced.tags


@pytest.mark.anyio
async def test_delete_and_not_found(memory_manager: MemoryManager):
    record = make_record("m4")
    await memory_manager.remember(record)
    await memory_manager.delete("m4")

    with pytest.raises(Exception):
        await memory_manager.recall("m4")


@pytest.mark.anyio
async def test_search_by_text_and_tags(memory_manager: MemoryManager):
    await memory_manager.remember(make_record("m5"))
    await memory_manager.remember(make_record("m6", namespace="other"))

    results = await memory_manager.search(SearchQuery(text="title m5", limit=5))
    assert len(results) == 1
    assert results[0].record.id == "m5"

    results = await memory_manager.search(SearchQuery(tags=("tag1",), limit=5))
    assert {res.record.id for res in results} == {"m5", "m6"}

    results = await memory_manager.search(SearchQuery(namespace="other", limit=5))
    assert len(results) == 1
    assert results[0].record.namespace == "other"


@pytest.mark.anyio
async def test_recent_and_important(memory_manager: MemoryManager):
    first = make_record("m7")
    second = make_record("m8")
    await memory_manager.remember(first)
    await memory_manager.remember(second)

    await memory_manager.recall("m7")
    recent = await memory_manager.search(SearchQuery(text="", limit=2))
    assert len(recent) == 2

    important = await memory_manager.search(SearchQuery(text="", limit=2))
    assert any(item.record.id == "m7" for item in important)


@pytest.mark.anyio
async def test_cleanup_and_expire_with_policies(logger_factory: LoggerFactory, event_bus: EventBus):
    container = Container()
    container.register_instance(LoggerFactory, logger_factory)
    container.register_instance(EventBus, event_bus)
    container.install(MemoryModule(retention_policy=RetentionManager(TTL(1))))
    manager = await container.resolve(MemoryManager)

    old_time = datetime.now(timezone.utc) - timedelta(seconds=10)
    stale = MemoryRecord(
        id="m9",
        owner_id="owner",
        namespace="default",
        title="Stale",
        content={"text": "old"},
        metadata={"source": "tests"},
        tags=("tag1",),
        importance=0,
        created_at=old_time,
        updated_at=old_time,
        last_accessed=old_time,
    )
    await manager.remember(stale)
    await manager.cleanup()

    with pytest.raises(Exception):
        await manager.recall("m9")

    latest = make_record("m10")
    await manager.remember(latest)
    manager._retention_manager = RetentionManager(LeastRecentlyUsed(max_records=1))
    await manager.cleanup()
    stats = await manager.stats()
    assert stats.total_records == 1

    manager._retention_manager = RetentionManager(ImportanceThreshold(threshold=5))
    await manager.cleanup()
    assert (await manager.stats()).total_records == 0


@pytest.mark.anyio
async def test_lifecycle_start_shutdown(memory_manager: MemoryManager):
    await memory_manager.start()
    await memory_manager.shutdown()
    # repeated shutdown should be idempotent
    await memory_manager.shutdown()


@pytest.mark.anyio
async def test_di_integration_and_event_publishing(logger_factory: LoggerFactory, event_bus: EventBus):
    container = Container()
    container.register_instance(LoggerFactory, logger_factory)
    container.register_instance(EventBus, event_bus)
    container.install(MemoryModule())
    manager = await container.resolve(MemoryManager)

    events = []

    async def handler(event: Event):
        events.append(event.name)

    event_bus.subscribe(MemoryStored, handler)
    event_bus.subscribe(MemoryAccessed, handler)
    event_bus.subscribe(MemoryUpdated, handler)
    event_bus.subscribe(MemoryDeleted, handler)
    event_bus.subscribe(MemoryForgotten, handler)

    await manager.remember(make_record("m11"))
    await manager.recall("m11")
    await manager.update("m11", title="mutated")
    await manager.delete("m11")

    assert set(events) == {"MemoryStored", "MemoryAccessed", "MemoryUpdated", "MemoryDeleted"}


@pytest.mark.anyio
async def test_concurrency_safety(logger_factory: LoggerFactory, event_bus: EventBus):
    container = Container()
    container.register_instance(LoggerFactory, logger_factory)
    container.register_instance(EventBus, event_bus)
    container.install(MemoryModule())
    manager = await container.resolve(MemoryManager)

    async def store_record(record_id: str):
        await manager.remember(make_record(record_id))
        return await manager.recall(record_id)

    results = await asyncio.gather(*(store_record(f"c{i}") for i in range(10)))
    assert len(results) == 10
    assert {record.id for record in results} == {f"c{i}" for i in range(10)}


@pytest.mark.anyio
async def test_stats_and_list(memory_manager: MemoryManager):
    await memory_manager.remember(make_record("m12", owner_id="ownerA", namespace="nsA"))
    await memory_manager.remember(make_record("m13", owner_id="ownerB", namespace="nsB"))

    stats = await memory_manager.stats()
    assert stats.total_records == 2
    assert stats.namespaces == 2

    list_ns = await memory_manager.list(namespace="nsA")
    assert len(list_ns) == 1
    assert list_ns[0].owner_id == "ownerA"

    list_owner = await memory_manager.list(owner_id="ownerB")
    assert len(list_owner) == 1
    assert list_owner[0].namespace == "nsB"
