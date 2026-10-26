"""The document-agent services, wired together.

Four collaborators that a driving adapter needs as a set: reading, citing,
showing a page, and showing where an answer came from (#363). Bundled so the
adapter resolves one thing from the container instead of four, and so adding a
use case does not change every signature between the composition root and the
tools.

Not an aggregate service: it holds no logic and forwards nothing. Each field
is the use case that owns its question.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

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
