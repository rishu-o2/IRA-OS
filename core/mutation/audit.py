from typing import List

from core.logging import Logger
from .contracts import AuditSink
from .exceptions import AuditError
from .models import AuditRecord


class AuditManager:
    """
    Coordinates dispatching AuditRecords to multiple registered AuditSinks.
    """

    def __init__(self, logger: Logger) -> None:
        self._sinks: List[AuditSink] = []
        self._logger = logger

    def register_sink(self, sink: AuditSink) -> None:
        """Register a new destination for audit records."""
        self._sinks.append(sink)

    async def record(self, record: AuditRecord) -> None:
        """
        Dispatch the record to all registered sinks.
        If any sink fails, we log it, but if ALL sinks fail and auditing is 
        critical, we raise an AuditError. For now, we raise if the first fails.
        """
        if not self._sinks:
            self._logger.warning("No AuditSinks registered. Audit record dropped.", audit_id=record.audit_id)
            return

        failures = 0
        for sink in self._sinks:
            try:
                await sink.record(record)
            except Exception as e:
                self._logger.error("AuditSink failed to record.", sink=type(sink).__name__, error=str(e))
                failures += 1

        if failures == len(self._sinks):
            raise AuditError(f"All {failures} AuditSinks failed to record audit_id: {record.audit_id}")


class InMemoryAuditSink(AuditSink):
    """
    A simple in-memory sink for scaffolding and testing.
    """

    def __init__(self) -> None:
        self.records: List[AuditRecord] = []

    async def record(self, record: AuditRecord) -> None:
        self.records.append(record)
