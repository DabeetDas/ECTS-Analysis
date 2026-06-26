from __future__ import annotations

import re

from pipeline_backend.schemas import MetricInsight


class InsightVerifier:
    def verify(self, insights: list[MetricInsight]) -> list[MetricInsight]:
        verified: list[MetricInsight] = []
        for insight in insights:
            warnings = list(insight.verifier_warnings)
            text = insight.analyst_takeaway.lower()
            if insight.coverage == "fy25" and re.search(r"\byoy\b|year[- ]on[- ]year|from fy\d{2}", text):
                warnings.append("FY25-only metric contains YoY language; review synthesis.")
            if insight.evidence_strength == "weak" and "evidence" in text and "weak" not in text:
                warnings.append("Weak-evidence insight may overstate transcript support.")
            if insight.needs_analyst_note:
                warnings.append("No direct transcript evidence found; ask the user for analyst context if this metric is important.")
            verified.append(insight.model_copy(update={"verifier_warnings": warnings}))
        return verified
