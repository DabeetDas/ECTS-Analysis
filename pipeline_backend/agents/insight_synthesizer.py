from __future__ import annotations

from pipeline_backend.schemas import MetricInsight
from pipeline_backend.tools.groq_client import GroqChatClient

SYSTEM_PROMPT = """You are a senior banking analyst.
Use only the provided financial values, numeric notes, and transcript evidence.
Do not invent numbers, transcript quotes, or causality.
For FY25-only metrics, do not discuss YoY movement.
If evidence is weak, say the explanation is based mainly on numeric decomposition."""

class LlamaInsightSynthesizer:
    def __init__(self, client: GroqChatClient | None = None) -> None:
        self.client = client or GroqChatClient()

    def synthesize(self, *, bank_name: str | None, insights: list[MetricInsight]) -> list[MetricInsight]:
        synthesized: list[MetricInsight] = []
        for insight in insights:
            try:
                takeaway = self.client.complete(
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=build_prompt(bank_name=bank_name, insight=insight),
                    max_tokens=900,
                )
                synthesized.append(insight.model_copy(update={"analyst_takeaway": takeaway.strip() or insight.analyst_takeaway}))
            except Exception as exc:
                warning = f"LLaMA synthesis unavailable for {insight.metric_key}: {exc}"
                synthesized.append(
                    insight.model_copy(update={"verifier_warnings": [*insight.verifier_warnings, warning]})
                )
        return synthesized



def build_prompt(*, bank_name: str | None, insight: MetricInsight) -> str:
    evidence = "\n".join(
        f"[{index + 1}] {item.topic} ({item.source_chunk_id}): {item.excerpt}"
        for index, item in enumerate(insight.evidence[:6])
    )
    previous = (
        f"Previous: {insight.previous_value} in {insight.previous_period}"
        if insight.previous_period
        else "Previous: not available"
    )
    notes = "\n".join(f"- {note}" for note in insight.numeric_notes)
    return f"""Bank: {bank_name or 'Unknown'}
Metric: {insight.label}
Coverage: {insight.coverage}
Current: {insight.current_value} in {insight.current_period}
{previous}
Evidence strength: {insight.evidence_strength}
Needs analyst note: {insight.needs_analyst_note}

Numeric notes:
{notes or '- None'}

Transcript evidence:
{evidence or 'No direct transcript evidence found.'}

Write 2-3 concise paragraphs explaining the number with management commentary. Cite evidence by [1], [2] where used."""
