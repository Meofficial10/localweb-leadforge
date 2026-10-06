"""Source adapter interface. All sources normalize to a common Place model."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class Place:
    source: str
    source_place_id: str
    name: str
    category: str | None = None
    address: str | None = None
    lat: float | None = None
    lng: float | None = None
    rating: float | None = None
    review_count: int | None = None
    website: str | None = None
    phone: str | None = None
    raw: dict | None = field(default_factory=dict)


class SourceAdapter(Protocol):
    name: str

    def search(self, city: str, categories: list[str]) -> list[Place]:
        """Return candidate places. Adapters must NOT filter by website; the pipeline does."""
        ...
