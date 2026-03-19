from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class AnalysisConfig:
    include: tuple[str, ...] = field(default_factory=tuple)
    exclude: tuple[str, ...] = field(default_factory=tuple)
    internal_only: bool = False

