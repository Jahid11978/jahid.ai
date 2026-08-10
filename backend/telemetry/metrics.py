from __future__ import annotations

from collections import defaultdict
from threading import Lock


class MetricsRegistry:
    """Small dependency-free metrics registry for local/dev operation.

    Production exporters can consume the same counters and histograms without
    coupling agents to a metrics vendor.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: dict[str, float] = defaultdict(float)
        self._samples: dict[str, list[float]] = defaultdict(list)

    def increment(self, name: str, value: float = 1.0) -> None:
        with self._lock:
            self._counters[name] += value

    def observe(self, name: str, value: float) -> None:
        with self._lock:
            self._samples[name].append(value)

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "counters": dict(self._counters),
                "samples": {k: list(v) for k, v in self._samples.items()},
            }
