from __future__ import annotations

from collections import defaultdict

from pipeline_backend.schemas import EvidenceItem, ExtractedFinancials, MetricInsight, MetricValue
from pipeline_backend.tools.financial_schema import METRIC_SPECS


class EvidenceLinker:
    def link(
        self,
        *,
        financials: ExtractedFinancials,
        evidence_by_metric: dict[str, list[EvidenceItem]],
    ) -> list[MetricInsight]:
        grouped: dict[str, list[MetricValue]] = defaultdict(list)
        for metric in financials.metrics:
            grouped[metric.metric_key].append(metric)

        insights: list[MetricInsight] = []
        for metric_key, values in grouped.items():
            spec = METRIC_SPECS.get(metric_key)
            if not spec:
                continue
            ordered = sorted(values, key=lambda item: fiscal_sort_key(item.period))
            current = ordered[-1]
            previous = ordered[-2] if spec.coverage == "multi-year" and len(ordered) > 1 else None
            evidence = evidence_by_metric.get(metric_key, [])
            strength = evidence_strength(evidence)
            notes = numeric_notes(metric_key, ordered, current, previous)
            insights.append(
                MetricInsight(
                    metric_key=metric_key,
                    label=spec.label,
                    coverage=spec.coverage,  # type: ignore[arg-type]
                    current_period=current.period,
                    current_value=current.value,
                    previous_period=previous.period if previous else None,
                    previous_value=previous.value if previous else None,
                    evidence_strength=strength,  # type: ignore[arg-type]
                    evidence=evidence,
                    numeric_notes=notes,
                    analyst_takeaway=local_takeaway(spec.label, current, previous, strength),
                    needs_analyst_note=strength == "weak",
                )
            )
        return sorted(insights, key=lambda item: item.metric_key)


def evidence_strength(evidence: list[EvidenceItem]) -> str:
    if any(item.match_type == "direct" for item in evidence):
        return "direct"
    if any(item.match_type == "expanded" for item in evidence):
        return "expanded"
    if evidence:
        return "keyword"
    return "weak"


def numeric_notes(metric_key: str, values: list[MetricValue], current: MetricValue, previous: MetricValue | None) -> list[str]:
    spec = METRIC_SPECS.get(metric_key)
    if not spec:
        return []
    if spec.coverage == "fy25":
        return [f"{spec.label} is available for {current.period}; no YoY movement is inferred unless the presentation provides more periods."]
    if not previous:
        return [f"{spec.label} has no prior period available for comparison."]
    direction = "increased" if current.value > previous.value else "declined" if current.value < previous.value else "was flat"
    return [f"{spec.label} {direction} from {previous.value} in {previous.period} to {current.value} in {current.period}."]


def local_takeaway(label: str, current: MetricValue, previous: MetricValue | None, strength: str) -> str:
    if previous:
        return f"{label} is {current.value} in {current.period}, compared with {previous.value} in {previous.period}. Evidence strength: {strength}."
    return f"{label} is {current.value} in {current.period}. Evidence strength: {strength}."


def fiscal_sort_key(period: str) -> tuple[int, str]:
    digits = "".join(ch for ch in str(period) if ch.isdigit())
    return (int(digits) if digits else 0, period)
