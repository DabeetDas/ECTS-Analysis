// Typed API client for the agentic upload pipeline backend (port 8100)

const PIPELINE_BASE = process.env.NEXT_PUBLIC_PIPELINE_API_URL ?? "http://localhost:8100";

// ─── Schema types (mirror pipeline_backend/schemas.py) ────────────────────────

export type MetricFormat = "crore" | "percent" | "number";
export type MetricCoverage = "fy25" | "multi-year" | "unknown";
export type EvidenceStrength = "direct" | "expanded" | "keyword" | "weak";

export interface SourceRef {
    document_type: "presentation" | "transcript" | "derived";
    page: number | null;
    slide: number | null;
    chunk_id: string | null;
    text: string | null;
}

export interface MetricValue {
    metric_key: string;
    label: string;
    period: string;
    value: number;
    unit: MetricFormat;
    source: SourceRef | null;
    confidence: number;
}

export interface ExtractedFinancials {
    bank_name: string | null;
    periods: string[];
    metrics: MetricValue[];
    warnings: string[];
    raw_payload: Record<string, unknown>;
}

export interface TranscriptChunk {
    chunk_id: string;
    text: string;
    source_name: string | null;
    period: string | null;
}

export interface PipelineEvidenceItem {
    metric_key: string;
    topic: string;
    excerpt: string;
    source_chunk_id: string | null;
    score: number;
    match_type: EvidenceStrength;
}

export interface PipelineMetricInsight {
    metric_key: string;
    label: string;
    coverage: MetricCoverage;
    current_period: string | null;
    current_value: number | null;
    previous_period: string | null;
    previous_value: number | null;
    evidence_strength: EvidenceStrength;
    evidence: PipelineEvidenceItem[];
    numeric_notes: string[];
    analyst_takeaway: string;
    needs_analyst_note: boolean;
    verifier_warnings: string[];
}

export interface PipelineResult {
    run_id: string;
    plan: string[];
    financials: ExtractedFinancials | null;
    transcript_chunks: TranscriptChunk[];
    insights: PipelineMetricInsight[];
    warnings: string[];
    analyst_note?: string | null;
}

// ─── API helpers ──────────────────────────────────────────────────────────────

async function post<T>(path: string, body?: FormData | string): Promise<T> {
    const isForm = body instanceof FormData;
    const response = await fetch(`${PIPELINE_BASE}${path}`, {
        method: "POST",
        headers: isForm ? undefined : body ? { "Content-Type": "application/json" } : undefined,
        body: body ?? undefined,
    });
    if (!response.ok) {
        const text = await response.text().catch(() => response.statusText);
        throw new Error(`Pipeline API error ${response.status}: ${text}`);
    }
    return response.json() as Promise<T>;
}

async function get<T>(path: string): Promise<T> {
    const response = await fetch(`${PIPELINE_BASE}${path}`);
    if (!response.ok) {
        throw new Error(`Pipeline API error ${response.status}: ${response.statusText}`);
    }
    return response.json() as Promise<T>;
}

// ─── Pipeline endpoints ────────────────────────────────────────────────────────

export async function createRun(): Promise<{ run_id: string }> {
    return post("/api/runs");
}

export async function uploadFiles(
    runId: string,
    presentation: File | null,
    transcript: File | null,
    analystNote?: string | null
): Promise<PipelineResult> {
    const form = new FormData();
    if (presentation) form.append("presentation", presentation);
    if (transcript) form.append("transcript", transcript);
    if (analystNote) form.append("analyst_note", analystNote);
    return post(`/api/runs/${runId}/upload`, form);
}

export async function extractFinancials(runId: string): Promise<PipelineResult> {
    return post(`/api/runs/${runId}/extract-financials`);
}

export async function retrieveEvidence(runId: string): Promise<PipelineResult> {
    return post(`/api/runs/${runId}/retrieve-evidence`);
}

export async function generateInsights(runId: string): Promise<PipelineResult> {
    return post(`/api/runs/${runId}/generate-insights`);
}

export async function getRun(runId: string): Promise<PipelineResult> {
    return get(`/api/runs/${runId}`);
}
