from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

MetricFormat = Literal["crore", "percent", "number"]
MetricCoverage = Literal["fy25", "multi-year", "unknown"]
EvidenceStrength = Literal["direct", "expanded", "keyword", "weak"]


class SourceRef(BaseModel):
    document_type: Literal["presentation", "transcript", "derived"] = "derived"
    page: int | None = None
    slide: int | None = None
    chunk_id: str | None = None
    text: str | None = None


class MetricValue(BaseModel):
    metric_key: str
    label: str
    period: str
    value: float
    unit: MetricFormat
    source: SourceRef | None = None
    confidence: float = 0.75


class ExtractedFinancials(BaseModel):
    bank_name: str | None = None
    periods: list[str] = Field(default_factory=list)
    metrics: list[MetricValue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class TranscriptChunk(BaseModel):
    chunk_id: str
    text: str
    source_name: str | None = None
    period: str | None = None


class EvidenceItem(BaseModel):
    metric_key: str
    topic: str
    excerpt: str
    source_chunk_id: str | None = None
    score: float
    match_type: EvidenceStrength


class MetricInsight(BaseModel):
    metric_key: str
    label: str
    coverage: MetricCoverage
    current_period: str | None = None
    current_value: float | None = None
    previous_period: str | None = None
    previous_value: float | None = None
    evidence_strength: EvidenceStrength
    evidence: list[EvidenceItem] = Field(default_factory=list)
    numeric_notes: list[str] = Field(default_factory=list)
    analyst_takeaway: str = ""
    needs_analyst_note: bool = False
    verifier_warnings: list[str] = Field(default_factory=list)


class PipelineResult(BaseModel):
    run_id: str
    plan: list[str] = Field(default_factory=list)
    financials: ExtractedFinancials | None = None
    transcript_chunks: list[TranscriptChunk] = Field(default_factory=list)
    insights: list[MetricInsight] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    analyst_note: str | None = None
    uploaded_files: dict[str, str | None] = Field(default_factory=dict)

    @model_validator(mode="after")
    def clean_uploaded_files(self) -> PipelineResult:
        self.uploaded_files = {k: v for k, v in self.uploaded_files.items() if v is not None}
        return self
