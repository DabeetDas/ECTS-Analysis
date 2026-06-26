from __future__ import annotations

from pipeline_backend.schemas import EvidenceItem, TranscriptChunk
from pipeline_backend.tools.transcript_search import retrieve_metric_evidence


class ReACTTranscriptRetriever:
    """Tool-driven retriever that follows a small ReACT loop deterministically."""

    def retrieve(self, *, metric_keys: list[str], chunks: list[TranscriptChunk]) -> dict[str, list[EvidenceItem]]:
        evidence: dict[str, list[EvidenceItem]] = {}
        for metric_key in metric_keys:
            # Thought: retrieve direct and adjacent transcript commentary for this metric.
            # Action: call the keyword/topic search tool.
            evidence[metric_key] = retrieve_metric_evidence(metric_key=metric_key, chunks=chunks)
            # Observation: evidence is ranked and returned for later synthesis.
        return evidence

