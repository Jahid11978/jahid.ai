from __future__ import annotations

import json
from .gateway import MemoryRecord


def export_records(records: list[MemoryRecord]) -> str:
    return json.dumps([record.to_dict() for record in records], ensure_ascii=False, indent=2, sort_keys=True)
