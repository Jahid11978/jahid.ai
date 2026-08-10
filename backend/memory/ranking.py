from __future__ import annotations

from .gateway import MemoryRecord


def rank(records: list[MemoryRecord], query: str) -> list[MemoryRecord]:
    terms = set(query.lower().split())

    def score(record: MemoryRecord) -> tuple[float, str]:
        words = set(record.content.lower().split())
        overlap = len(terms & words)
        return (overlap + record.confidence, record.updated_at)

    return sorted(records, key=score, reverse=True)
