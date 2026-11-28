"""AI Documentation Assistant package for SpecCraft AI."""

from speccraft.ai.enricher import (
    AIEnricherService,
    DiffChangeCard,
    DiffSummaryProposal,
    EnrichedEndpointProposal,
    OfflineFallbackEnricher,
    SchemaFieldExplanation,
    get_enricher_service,
)

__all__ = [
    "AIEnricherService",
    "DiffChangeCard",
    "DiffSummaryProposal",
    "EnrichedEndpointProposal",
    "OfflineFallbackEnricher",
    "SchemaFieldExplanation",
    "get_enricher_service",
]

