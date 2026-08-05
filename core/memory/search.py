from datetime import datetime, timezone
from typing import List

from .exceptions import SearchError
from .indexes import MemoryIndex
from .models import MemoryRecord, SearchQuery, SearchResult


def _score_record(record: MemoryRecord, query: SearchQuery) -> float:
    score = 0.0
    text = query.text.strip().lower()

    if text:
        if text in record.title.lower():
            score += 2.0
        if text in str(record.content).lower():
            score += 1.0
        if text in record.namespace.lower():
            score += 0.5
        for metadata_value in record.metadata.values():
            if text in str(metadata_value).lower():
                score += 0.5

    if query.tags:
        matching_tags = len(set(query.tags) & set(record.tags))
        score += matching_tags * 1.0

    return score


class SearchEngine:
    """Rule-based search over in-memory memory records."""

    def __init__(self, index: MemoryIndex) -> None:
        self._index = index

    def search(self, query: SearchQuery) -> List[SearchResult]:
        if query.limit <= 0:
            raise SearchError("Search limit must be at least 1.")

        if query.namespace:
            candidate_ids = self._index.get_by_namespace(query.namespace)
        else:
            candidate_ids = self._index.all_ids()

        results: List[SearchResult] = []
        for memory_id in candidate_ids:
            record = self._index._by_id.get(memory_id)
            if record is None:
                continue
            score = _score_record(record, query)
            if score > 0.0 or not query.text:
                results.append(SearchResult(record=record, score=score))

        results.sort(key=lambda item: (-item.score, item.record.updated_at))
        return results[:query.limit]

    def search_tags(self, tags: tuple[str, ...], namespace: str | None = None) -> List[SearchResult]:
        candidate_ids = set(self._index.all_ids())
        if namespace is not None:
            candidate_ids &= self._index.get_by_namespace(namespace)

        for tag in tags:
            candidate_ids &= self._index.get_by_tag(tag)

        results = [SearchResult(record=self._index._by_id[mid], score=1.0) for mid in candidate_ids]
        results.sort(key=lambda item: item.record.updated_at, reverse=True)
        return results

    def search_namespace(self, namespace: str) -> List[SearchResult]:
        return [SearchResult(record=self._index._by_id[mid], score=1.0) for mid in self._index.get_by_namespace(namespace)]

    def recent(self, limit: int = 10) -> List[SearchResult]:
        if limit <= 0:
            raise SearchError("Recent result limit must be at least 1.")
        records = [self._index._by_id[mid] for mid in self._index.all_ids()]
        records.sort(key=lambda record: record.last_accessed, reverse=True)
        return [SearchResult(record=record, score=1.0) for record in records[:limit]]

    def important(self, limit: int = 10) -> List[SearchResult]:
        if limit <= 0:
            raise SearchError("Important result limit must be at least 1.")
        records = [self._index._by_id[mid] for mid in self._index.all_ids()]
        records.sort(key=lambda record: (-record.importance, record.updated_at))
        return [SearchResult(record=record, score=float(record.importance)) for record in records[:limit]]
