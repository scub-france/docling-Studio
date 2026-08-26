"""The document-agent services, wired together.

Three collaborators that a driving adapter needs as a set: reading, citing,
and showing. Bundled so the adapter resolves one thing from the container
instead of three, and so adding a fourth use case does not change every
signature between the composition root and the tools.

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


@dataclass(frozen=True)
class DocumentTools:
    navigation: NavigationService
    citations: CitationService
    images: CitationImageService
