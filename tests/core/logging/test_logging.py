import os
import asyncio
import tempfile
import json as json_lib
from contextlib import contextmanager
from core.logging import (
    LogLevel, LogEntry, Logger, LoggerFactory,
    HumanFormatter, JsonFormatter,
    NullSink, ConsoleSink, FileSink,
    LogScope, set_correlation_id, new_correlation_id, get_context,
    LoggingModule,
)
from core.container import Container

@contextmanager
def assert_raises(exc_type, match=None):
    try:
        yield
    except exc_type as e:
        if match and match not in str(e):
            raise AssertionError(f"Expected message to match '{match}', got '{e}'")
    except Exception as e:
        raise AssertionError(f"Expected {exc_type.__name__}, got {type(e).__name__}: {e}")
    else:
        raise AssertionError(f"Expected {exc_type.__name__}, but no exception raised")


# ─── Level Tests ───────────────────────────────────────────────────────────────

def test_log_levels_ordered():
    assert LogLevel.TRACE < LogLevel.DEBUG
    assert LogLevel.DEBUG < LogLevel.INFO
    assert LogLevel.INFO < LogLevel.WARNING
    assert LogLevel.WARNING < LogLevel.ERROR
    assert LogLevel.ERROR < LogLevel.CRITICAL


# ─── Model Tests ───────────────────────────────────────────────────────────────

def test_log_entry_defaults():
    entry = LogEntry(level=LogLevel.INFO, logger="test", message="Hello")
    assert entry.level == LogLevel.INFO
    assert entry.logger == "test"
    assert entry.message == "Hello"
    assert entry.correlation_id is None
    assert entry.event_id is None
    assert entry.exception is None
    assert entry.metadata == {}


# ─── Formatter Tests ───────────────────────────────────────────────────────────

def test_human_formatter():
    formatter = HumanFormatter(colorize=False)
    entry = LogEntry(level=LogLevel.INFO, logger="core", message="hello")
    output = formatter.format(entry)
    assert "INFO" in output
    assert "core" in output
    assert "hello" in output

def test_human_formatter_with_exception():
    formatter = HumanFormatter(colorize=False)
    try:
        raise ValueError("oops")
    except ValueError as e:
        entry = LogEntry(level=LogLevel.ERROR, logger="core", message="boom", exception=e)
    output = formatter.format(entry)
    assert "ValueError" in output
    assert "oops" in output

def test_json_formatter():
    formatter = JsonFormatter()
    entry = LogEntry(
        level=LogLevel.WARNING,
        logger="brain.planner",
        message="degraded",
        correlation_id="abc-123",
        metadata={"task": "T1"}
    )
    output = formatter.format(entry)
    parsed = json_lib.loads(output)
    assert parsed["level"] == "WARNING"
    assert parsed["logger"] == "brain.planner"
    assert parsed["message"] == "degraded"
    assert parsed["correlation_id"] == "abc-123"
    assert parsed["metadata"]["task"] == "T1"

def test_json_formatter_with_exception():
    formatter = JsonFormatter()
    try:
        raise RuntimeError("test error")
    except RuntimeError as e:
        entry = LogEntry(level=LogLevel.ERROR, logger="core", message="crash", exception=e)
    output = formatter.format(entry)
    parsed = json_lib.loads(output)
    assert "exception" in parsed
    assert parsed["exception"]["type"] == "RuntimeError"


# ─── Sink Tests ────────────────────────────────────────────────────────────────

def test_null_sink_discards_entries():
    sink = NullSink()
    entry = LogEntry(level=LogLevel.INFO, logger="test", message="ignored")
    sink.emit(entry)  # Should not raise
    sink.flush()
    sink.close()

def test_console_sink_writes():
    import io
    stream = io.StringIO()
    sink = ConsoleSink(formatter=HumanFormatter(colorize=False), stream=stream)
    entry = LogEntry(level=LogLevel.INFO, logger="test", message="hello console")
    sink.emit(entry)
    sink.flush()
    output = stream.getvalue()
    assert "hello console" in output

def test_file_sink_writes():
    with tempfile.NamedTemporaryFile(mode='r', delete=False, suffix=".log") as f:
        path = f.name
    try:
        sink = FileSink(filepath=path, formatter=HumanFormatter(colorize=False))
        entry = LogEntry(level=LogLevel.DEBUG, logger="test", message="file check")
        sink.emit(entry)
        sink.close()
        with open(path) as f:
            content = f.read()
        assert "file check" in content
    finally:
        os.remove(path)

def test_file_sink_json_formatter():
    with tempfile.NamedTemporaryFile(mode='r', delete=False, suffix=".jsonl") as f:
        path = f.name
    try:
        sink = FileSink(filepath=path, formatter=JsonFormatter())
        entry = LogEntry(level=LogLevel.INFO, logger="test", message="json line", metadata={"k": "v"})
        sink.emit(entry)
        sink.close()
        with open(path) as f:
            parsed = json_lib.loads(f.readline())
        assert parsed["message"] == "json line"
        assert parsed["metadata"]["k"] == "v"
    finally:
        os.remove(path)


# ─── Logger Tests ──────────────────────────────────────────────────────────────

def test_logger_level_filtering():
    received = []

    class CaptureSink:
        def emit(self, entry): received.append(entry)
        def flush(self): pass
        def close(self): pass

    logger = Logger("test", level=LogLevel.WARNING, sinks=[CaptureSink()])
    logger.debug("should be filtered")
    logger.info("also filtered")
    logger.warning("should pass")

    assert len(received) == 1
    assert received[0].level == LogLevel.WARNING

def test_logger_all_levels():
    received = []

    class CaptureSink:
        def emit(self, entry): received.append(entry)
        def flush(self): pass
        def close(self): pass

    logger = Logger("test", level=LogLevel.TRACE, sinks=[CaptureSink()])
    logger.trace("t")
    logger.debug("d")
    logger.info("i")
    logger.warning("w")
    logger.error("e")
    logger.critical("c")
    assert len(received) == 6

def test_child_logger_hierarchy():
    received = []

    class CaptureSink:
        def emit(self, entry): received.append(entry)
        def flush(self): pass
        def close(self): pass

    parent = Logger("core", level=LogLevel.DEBUG, sinks=[CaptureSink()])
    child = parent.child("events")
    grandchild = child.child("bus")

    grandchild.info("from grandchild")

    # Should propagate to parent's sink
    assert len(received) == 1
    assert received[0].logger == "core.events.bus"

def test_child_logger_inherits_level():
    parent = Logger("root", level=LogLevel.ERROR, sinks=[])
    child = parent.child("module")
    assert child.effective_level == LogLevel.ERROR


# ─── Context Propagation Tests ────────────────────────────────────────────────

def test_context_propagation():
    received = []

    class CaptureSink:
        def emit(self, entry): received.append(entry)
        def flush(self): pass
        def close(self): pass

    with LogScope("test-scope", correlation_id="cid-xyz"):
        logger = Logger("test.ctx", level=LogLevel.DEBUG, sinks=[CaptureSink()])
        logger.info("contextual message")

    assert len(received) == 1
    assert received[0].correlation_id == "cid-xyz"

def test_new_correlation_id():
    cid = new_correlation_id()
    assert cid is not None
    ctx = get_context()
    assert ctx.correlation_id == cid

def test_log_scope_restores_context():
    original_ctx = get_context()
    with LogScope("scope", correlation_id="scoped-cid"):
        inner_ctx = get_context()
        assert inner_ctx.correlation_id == "scoped-cid"
    outer_ctx = get_context()
    assert outer_ctx.correlation_id == original_ctx.correlation_id


# ─── Factory Tests ─────────────────────────────────────────────────────────────

def test_factory_caches_loggers():
    factory = LoggerFactory(sinks=[NullSink()])
    a = factory.get("core.events")
    b = factory.get("core.events")
    assert a is b

def test_factory_wires_hierarchy():
    received = []

    class CaptureSink:
        def emit(self, entry): received.append(entry)
        def flush(self): pass
        def close(self): pass

    factory = LoggerFactory(level=LogLevel.DEBUG, sinks=[CaptureSink()])
    root = factory.get("core")
    child = factory.get("core.events")
    grandchild = factory.get("core.events.bus")

    grandchild.info("dispatched from bus")
    # root sink catches it via hierarchy
    assert any(e.logger == "core.events.bus" for e in received)


# ─── DI Integration Tests ──────────────────────────────────────────────────────

def test_di_integration():
    factory = LoggerFactory(sinks=[NullSink()])
    module = LoggingModule(factory)
    container = Container()
    container.install(module)

    async def run():
        resolved_factory = await container.resolve(LoggerFactory)
        resolved_logger = await container.resolve(Logger)
        assert resolved_factory is factory
        assert isinstance(resolved_logger, Logger)

    asyncio.run(run())
