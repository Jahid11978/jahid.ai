from __future__ import annotations

from collections import defaultdict
from threading import Lock


class MetricsRegistry:
    """Small dependency-free metrics registry for local/dev operation.

    Production exporters can consume the same counters and histograms without
    coupling agents to a metrics vendor.
    """

    def __init__(self) -> None:
        """Start with independent, empty counters and sample lists."""
        self._lock = Lock()
        self._counters: dict[str, float] = defaultdict(float)
        self._samples: dict[str, list[float]] = defaultdict(list)

    def increment(self, name: str, value: float = 1.0) -> None:
        """Add to a named counter, starting at zero for a new name.

        A negative value decreases the counter.
        """
        with self._lock:
            self._counters[name] += value

    def observe(self, name: str, value: float) -> None:
        """Store a raw sample for a name without assigning a unit or aggregating."""
        with self._lock:
            self._samples[name].append(value)

    def snapshot(self) -> dict[str, object]:
        """Return copies of counter totals and sample lists by name."""
        with self._lock:
            return {
                "counters": dict(self._counters),
                "samples": {k: list(v) for k, v in self._samples.items()},
            }
