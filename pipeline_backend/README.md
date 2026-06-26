# Agentic Upload Pipeline

Standalone service for the investor-presentation + earnings-call workflow.

It is intentionally separate from the existing `backend/` app.

## Flow

1. Create a run.
2. Upload investor presentation and transcript.
3. Gemini extracts financials from the presentation.
4. Deterministic tools normalize values to the `data_new.xlsx`-style schema.
5. ReACT-style transcript retrieval finds direct, adjacent, and keyword evidence.
6. LLaMA-3.3-70B via Groq synthesizes grounded analyst insight.
7. A verifier flags unsupported claims and invalid YoY language for FY25-only metrics.

## Run

```bash
pip install -r pipeline_backend/requirements.txt
export GEMINI_API_KEY=...
export GROQ_API_KEY=...
PYTHONPATH=. uvicorn pipeline_backend.main:app --reload --port 8100
```

## API

```bash
curl -X POST http://localhost:8100/api/runs
```

```bash
curl -X POST http://localhost:8100/api/runs/{run_id}/upload \
  -F presentation=@presentation.pdf \
  -F transcript=@earnings_call.txt
```

```bash
curl -X POST http://localhost:8100/api/runs/{run_id}/run
```

For development without Gemini, upload a JSON file as `presentation` using the expected extraction shape; the service will normalize it directly.
