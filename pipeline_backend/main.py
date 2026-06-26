from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

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


app = FastAPI(title="ECTS Agentic Upload Pipeline")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

store = get_run_store()
planner = ReWOOPlanner()


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