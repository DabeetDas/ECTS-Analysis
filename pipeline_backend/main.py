from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

from llm import normalize_json_response
from pipeline_backend.agents.evidence_linker import EvidenceLinker
from pipeline_backend.agents.financial_extractor import GeminiFinancialExtractor
from pipeline_backend.agents.insight_synthesizer import LlamaInsightSynthesizer
from pipeline_backend.agents.planner import ReWOOPlanner
from pipeline_backend.agents.transcript_retriever import ReACTTranscriptRetriever
from pipeline_backend.agents.verifier import InsightVerifier
from pipeline_backend.schemas import PipelineResult
from pipeline_backend.storage.run_store import get_run_store
from pipeline_backend.tools.document_parser import chunk_transcript, extract_text
from pipeline_backend.tools.financial_normalizer import normalize_extracted_payload

load_dotenv()

app = FastAPI(title="ECTS Agentic Upload Pipeline")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

store = get_run_store()
planner = ReWOOPlanner()


class MetricDefinition(BaseModel):
    key: Optional[str] = None
    label: str
    format: Optional[str] = None
    coverage: str
    better: Optional[str] = None
    topics: Optional[List[str]] = []
    keywords: Optional[List[str]] = []
    adjacentMetrics: Optional[List[str]] = []


class EvidenceItem(BaseModel):
    topic: str
    excerpt: str
    callDate: str
    quarter: Optional[str] = None
    score: Optional[float] = 0
    matchType: Optional[str] = "direct"


class InsightPayload(BaseModel):
    metric: MetricDefinition
    currentYear: str
    currentValue: str
    previousYear: Optional[str] = None
    previousValue: Optional[str] = None
    absoluteChange: Optional[str] = None
    percentChange: Optional[str] = None
    evidence: List[EvidenceItem] = []
    evidenceStrength: str
    numericNotes: List[str] = []


class MetricRequest(BaseModel):
    bankCode: str
    insight: InsightPayload


METRIC_CONTEXT = {
    "gnpa_pct": "GNPA (Gross Non-Performing Assets) is Gross NPA / Gross Advances. Commentary on 'asset quality', 'slippages', 'bad loans', and 'provisioning' directly impacts this metric.",
    "roa_pct": "ROA (Return on Assets) is Net Profit / Average Assets. Commentary on 'profitability', 'yields', 'operating expenses', and 'interest income' directly impacts this metric.",
    "nim_pct": "NIM (Net Interest Margin) is (Interest Income - Interest Expense) / Average Earning Assets. Commentary on 'cost of funds', 'yield on advances', and 're-pricing of loans' is highly relevant.",
    "z_score": "Bank Z-Score = (ROA + Equity/Assets) / Volatility(ROA). It measure stability and default risk. Components: 1) Profitability (ROA), 2) Capital Adequacy (Equity/Assets), 3) Earnings Stability (Volatility of ROA). Look for commentary on advances growth, capital ratios, and income stability.",
    "casa_pct": "CASA % = (Current + Savings Accounts) / Total Deposits. It represents low-cost funding. Look for 'deposit franchise', 'granularity', and 'savings growth' commentary.",
    "efficiency_ratio_pct": "Efficiency Ratio = Operating Expenses / Net Income. Measures cost control. Look for 'digitization', 'staff costs', and 'branch expansion' commentary.",
    "crar_pct": "CRAR (Capital Adequacy Ratio) = Capital / Risk Weighted Assets. Look for mentions of 'tier 1 capital', 'capital infusion', and 'RWA optimization'."
}


def build_prompt(bank_code: str, insight: InsightPayload) -> str:
    metric_key = insight.metric.key or ""
    metric_def = METRIC_CONTEXT.get(metric_key, "No specific formula provided.")
    is_fy25 = insight.metric.coverage == "fy25"

    if is_fy25:
        movement = f"{insight.metric.label}: {insight.currentValue} in {insight.currentYear}\nNo year-on-year comparison available from the uploaded workbook."
    else:
        if insight.previousYear and insight.previousValue:
            movement = f"{insight.metric.label}: {insight.previousValue} in {insight.previousYear} to {insight.currentValue} in {insight.currentYear}. Absolute change: {insight.absoluteChange or 'N/A'}. Percent change: {insight.percentChange or 'N/A'}."
        else:
            movement = f"{insight.metric.label}: {insight.currentValue} in {insight.currentYear}. Year-on-year movement is not available from the uploaded workbook."

    evidence_lines = []
    for i, item in enumerate(insight.evidence[:6]):
        period = item.quarter or "Transcript"
        evidence_lines.append(f"{i+1}. Topic: {item.topic}; Period: {period} {item.callDate}; Excerpt: {item.excerpt}")
    
    evidence_text = "\n".join(evidence_lines)
    numeric_notes_text = "\n".join([f"- {note}" for note in insight.numericNotes])

    return f"""Bank: {bank_code}
Metric coverage: {insight.metric.coverage}
Evidence strength: {insight.evidenceStrength}

Metric Details:
{movement}

Metric Formula/Context:
{metric_def}

Financial Decomposition Tool Output (Numeric breakdown):
{numeric_notes_text or '- Not available'}

Keyword / Adjacent Topic Transcript Evidence (Indexed):
{evidence_text or 'No direct transcript evidence was found.'}

Write a comprehensive, professional financial analysis of this metric.
- Your analysis MUST be grounded in the provided Evidence.
- Use explicit citations (e.g., [1], [3]) when referencing specific management commentary.
- Bridge the numeric movement shown in the 'Financial Decomposition' with the qualitative themes in the 'Transcript Evidence'.
- Provide multiple paragraphs of expert synthesis.
- Maintain a senior analyst tone."""


@app.post("/api/metric-insight")
async def get_metric_insight(request: MetricRequest):
    groq_key = os.environ.get("GROQ_API_KEY", "").strip().strip('"').strip("'")
    if not groq_key:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY is not configured.")

    is_fy25 = request.insight.metric.coverage == "fy25"
    if is_fy25:
        system_prompt = """You are a senior banking analyst. Evaluate this FY25-only metric based on the provided data.
- Directly bridge the numeric decomposition with specific management commentary found in the evidence.
- Quote or explicitly paraphrase management's language to back your assertions.
- Do not compute trends or mention year-on-year comparisons.
- Provide 2-3 detailed paragraphs of grounded synthesis."""
    else:
        system_prompt = """You are a senior banking analyst. Provide a concise, evidence-backed analysis of this multi-year metric in 2–3 focused paragraphs.
- Lead with the 'why' behind key movements, citing specific transcript evidence (e.g., 'As noted in the 2024 calls...', 'Management highlighted...').
- Connect numeric trends directly to strategic shifts or operational risks — no filler.
- Be direct and precise. Omit preamble, summaries, and repetition.
- Maintain a professional, expert tone throughout."""

    user_prompt = build_prompt(request.bankCode, request.insight)
    model = os.environ.get("INSIGHTS_MODEL") or "llama-3.3-70b-versatile"

    try:
        from groq import Groq
        client = Groq(api_key=groq_key)
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "ask_user_analyst_note",
                    "description": "Invoke this tool if there is completely insufficient management commentary or evidence to explain the metric.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reason": {"type": "string"}
                        },
                        "required": ["reason"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_indian_news",
                    "description": "Search latest news from Indian financial papers (ET, Mint, BS) to enrich context. Use for recent events not in transcripts.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query, e.g., 'HDFC Bank GNPA trends 2024'"}
                        },
                        "required": ["query"]
                    }
                }
            }
        ]

        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            tools=tools,
            tool_choice="auto",
            temperature=0,
            max_tokens=2048
        )

        message = completion.choices[0].message
        if message.tool_calls:
            tool_call = next((tc for tc in message.tool_calls if tc.function.name == "ask_user_analyst_note"), None)
            if tool_call:
                return {"askUser": True}
        return {"takeaway": message.content}

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


@app.post("/api/runs")
def create_run() -> dict[str, str]:
    return {"run_id": store.create_run()}


@app.post("/api/runs/{run_id}/upload")
async def upload_run_files(
    run_id: str,
    presentation: UploadFile | None = File(default=None),
    transcript: UploadFile | None = File(default=None),
    analyst_note: str | None = Form(default=None),
) -> PipelineResult:
    saved: dict[str, str] = {}
    if presentation:
        key = await save_upload(run_id, presentation, "presentation")
        saved["presentation"] = key
    if transcript:
        key = await save_upload(run_id, transcript, "transcript")
        saved["transcript"] = key
    if not saved:
        raise HTTPException(status_code=400, detail="Upload at least one file")

    # track uploaded filenames in result so we can find them later without glob
    result = store.read_result(run_id)
    result.plan = planner.plan()
    if analyst_note is not None:
        result.analyst_note = analyst_note
    if not hasattr(result, "uploaded_files") or result.uploaded_files is None:
        result.uploaded_files = {}
    result.uploaded_files.update(saved)
    store.write_result(result)
    return result


@app.post("/api/runs/{run_id}/extract-financials")
def extract_financials(run_id: str) -> PipelineResult:
    result = store.read_result(run_id)
    presentation_key = find_uploaded_key(result, "presentation")
    if not presentation_key:
        raise HTTPException(status_code=404, detail="Presentation not uploaded")

    if presentation_key.endswith(".json"):
        filename = presentation_key.split("/")[-1]
        payload = store.read_json(run_id, filename)
        result.financials = normalize_extracted_payload(payload)
    else:
        # download to a temp file for local processing
        presentation_path = download_to_temp(run_id, presentation_key)
        result.financials = GeminiFinancialExtractor().extract(presentation_path)

    result.plan = result.plan or planner.plan()
    store.write_json(run_id, "extracted_financials.json", result.financials.model_dump())
    store.write_result(result)
    return result


@app.post("/api/runs/{run_id}/retrieve-evidence")
def retrieve_evidence(run_id: str) -> PipelineResult:
    result = store.read_result(run_id)
    if not result.financials:
        result = extract_financials(run_id)
    transcript_key = find_uploaded_key(result, "transcript")
    if not transcript_key:
        raise HTTPException(status_code=404, detail="Transcript not uploaded")

    transcript_path = download_to_temp(run_id, transcript_key)
    text = extract_text(transcript_path)
    result.transcript_chunks = chunk_transcript(text, source_name=transcript_path.name)
    metric_keys = sorted({metric.metric_key for metric in result.financials.metrics}) if result.financials else []
    evidence_by_metric = ReACTTranscriptRetriever().retrieve(metric_keys=metric_keys, chunks=result.transcript_chunks)
    result.insights = EvidenceLinker().link(financials=result.financials, evidence_by_metric=evidence_by_metric)
    store.write_result(result)
    return result


@app.post("/api/runs/{run_id}/generate-insights")
def generate_insights(run_id: str) -> PipelineResult:
    result = store.read_result(run_id)
    if not result.insights:
        result = retrieve_evidence(run_id)
    result.insights = LlamaInsightSynthesizer().synthesize(
        bank_name=result.financials.bank_name if result.financials else None,
        insights=result.insights,
    )
    result.insights = InsightVerifier().verify(result.insights)
    store.write_json(run_id, "insights.json", [item.model_dump() for item in result.insights])
    store.write_result(result)
    return result


@app.post("/api/runs/{run_id}/run")
def run_pipeline(run_id: str) -> PipelineResult:
    result = retrieve_evidence(run_id)
    result.insights = LlamaInsightSynthesizer().synthesize(
        bank_name=result.financials.bank_name if result.financials else None,
        insights=result.insights,
    )
    result.insights = InsightVerifier().verify(result.insights)
    store.write_result(result)
    return result


@app.get("/api/runs")
def list_runs() -> list[PipelineResult]:
    """Return all past runs for the history UI."""
    run_ids = store.list_runs()
    return [store.read_result(run_id) for run_id in run_ids]


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> PipelineResult:
    return store.read_result(run_id)


# ── helpers ───────────────────────────────────────────────────────────────────

async def save_upload(run_id: str, upload: UploadFile, prefix: str) -> str:
    import tempfile

    suffix = Path(upload.filename or "").suffix or ".bin"
    filename = f"{prefix}{suffix}"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await upload.read())
        tmp_path = Path(tmp.name)

    try:
        return store.save_upload(run_id, tmp_path, filename)
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass


def find_uploaded_key(result: PipelineResult, prefix: str) -> str | None:
    """Find an uploaded file key by prefix from the result metadata."""
    return result.uploaded_files.get(prefix)


def download_to_temp(run_id: str, filename: str) -> Path:
    """Download a file from the store to a local temp path for processing."""
    import tempfile
    data = store.read_bytes(run_id, filename)
    suffix = Path(filename).suffix
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(data)
    tmp.flush()
    return Path(tmp.name)