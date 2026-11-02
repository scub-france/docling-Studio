"""The document-agent services, wired together.

Four collaborators that a driving adapter needs as a set: reading, citing,
showing a page, and showing where an answer came from (#363). Bundled so the
adapter resolves one thing from the container instead of four, and so adding a
use case does not change every signature between the composition root and the
tools.

Not an aggregate service: it holds no logic and forwards nothing. Each field
is the use case that owns its question. `config` is the budgets the four were
built with: a runtime change (#364) builds a new set rather than mutating
this one, so a call in flight finishes on the budgets it started with.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from services.navigation_config import NavigationConfig

if TYPE_CHECKING:
    from services.citation_image_service import CitationImageService
    from services.citation_service import CitationService
    from services.navigation_service import NavigationService
    from services.source_service import SourceService


@dataclass(frozen=True)
class DocumentTools:
    navigation: NavigationService
    citations: CitationService
    images: CitationImageService
    sources: SourceService
    config: NavigationConfig = field(default_factory=NavigationConfig)
