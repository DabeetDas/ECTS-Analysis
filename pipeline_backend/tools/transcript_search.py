from __future__ import annotations

from pipeline_backend.schemas import EvidenceItem, TranscriptChunk
from pipeline_backend.tools.financial_schema import METRIC_SPECS, MetricSpec, normalize_label


def retrieve_metric_evidence(
    *,
    metric_key: str,
    chunks: list[TranscriptChunk],
    max_items: int = 8,
) -> list[EvidenceItem]:
    spec = METRIC_SPECS.get(metric_key)
    if not spec:
        return []
    direct_terms = {normalize_label(term) for term in spec.topics}
    expanded_terms = expanded_terms_for(spec)
    keyword_terms = {normalize_label(term) for term in spec.keywords}
    evidence: list[EvidenceItem] = []

    for chunk in chunks:
        sentences = split_sentences(chunk.text)
        for sentence in sentences:
            sentence_norm = normalize_label(sentence)
            direct_count = count_matches(sentence_norm, direct_terms)
            expanded_count = count_matches(sentence_norm, expanded_terms)
            keyword_count = count_matches(sentence_norm, keyword_terms)
            if direct_count == 0 and expanded_count == 0 and keyword_count == 0:
                continue
            match_type = "direct" if direct_count else "expanded" if expanded_count else "keyword"
            topic = first_matching_term(sentence_norm, direct_terms | expanded_terms | keyword_terms) or spec.label
            score = direct_count * 8 + expanded_count * 4 + keyword_count * 2 + min(len(sentence) / 120, 3)
            evidence.append(
                EvidenceItem(
                    metric_key=metric_key,
                    topic=topic,
                    excerpt=sentence.strip(),
                    source_chunk_id=chunk.chunk_id,
                    score=round(score, 2),
                    match_type=match_type,  # type: ignore[arg-type]
                )
            )

    return sorted(evidence, key=lambda item: item.score, reverse=True)[:max_items]


def expanded_terms_for(spec: MetricSpec) -> set[str]:
    terms: set[str] = set()
    for adjacent in spec.adjacent_metrics:
        adjacent_spec = METRIC_SPECS.get(adjacent)
        if adjacent_spec:
            terms.update(normalize_label(term) for term in adjacent_spec.topics)
            terms.update(normalize_label(term) for term in adjacent_spec.keywords)
    return terms


def split_sentences(text: str) -> list[str]:
    rough = text.replace("\n", " ").split(".")
    return [item.strip() for item in rough if len(item.strip()) > 30]


def count_matches(text: str, terms: set[str]) -> int:
    return sum(1 for term in terms if term and term in text)


def first_matching_term(text: str, terms: set[str]) -> str | None:
    for term in sorted(terms, key=len, reverse=True):
        if term and term in text:
            return term
    return None

