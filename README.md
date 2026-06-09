# ECTS Analysis

Small implementation of the Section 3 methodology from `ref_paper.pdf`:

- `TopicRetriever` extracts financial topics and short excerpts from document text.
- `TopicsOntology` stores topics as a directed acyclic graph rather than a tree.
- `OntologistAgent` checks whether topics already exist and inserts novel topics into the DAG.

The runtime LLM is OpenRouter through the OpenAI-compatible `openai` SDK, using `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` by default. This repo does not install or download dependencies; add them manually in your environment.
Local inference is supported in two ways: `--provider ollama` for an Ollama server, or `--provider qwen` to load a local Qwen Transformers checkpoint directory directly from disk.

## Run

Set your OpenRouter API key first:

```bash
export OPENROUTER_API_KEY=...
```

```bash
python3 -m ects_analysis.demo --input data/dummy_earnings_call.txt --output outputs/ontology.json --model nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free
```

If running directly from this folder without installing the package:

```bash
PYTHONPATH=src python3 -m ects_analysis.demo --input data/dummy_earnings_call.txt --output outputs/ontology.json --model nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free
```

The initial root and child topics come from [seed_topics.json](data/seed_topics.json). Pass a different file with `--seed-topics path/to/topics.json`.

For local Ollama inference:

```bash
PYTHONPATH=src python3 -m ects_analysis.demo \
  --provider ollama \
  --model /path/to/local/model
```

For direct local Qwen checkpoint inference, install `torch` and `transformers`, then pass the checkpoint directory:

```bash
PYTHONPATH=src python3 -m ects_analysis.demo \
  --provider qwen \
  --model /path/to/qwen-checkpoint-dir
```

The Qwen loader uses local files only by default. You can tune it with environment variables such as `TRANSFORMERS_MAX_INPUT_TOKENS`, `TRANSFORMERS_MAX_NEW_TOKENS`, `TRANSFORMERS_DEVICE_MAP`, `TRANSFORMERS_TORCH_DTYPE`, `TRANSFORMERS_LOCAL_FILES_ONLY`, `TRANSFORMERS_TRUST_REMOTE_CODE`, `TRANSFORMERS_LOAD_IN_4BIT`, `TRANSFORMERS_LOAD_IN_8BIT`, and `TRANSFORMERS_ENABLE_THINKING`.

## Test

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

## Frontend Dashboard

The dashboard UI now lives in a modern Next.js app under [frontend](frontend). The Python `visualize` module no longer renders raw HTML/CSS; it packages analysis output, the topic hierarchy, bank branding, and financial CSV data into JSON for the React frontend.

Export the dashboard data:

```bash
PYTHONPATH=src python3 -m ects_analysis.visualize \
  --input outputs/psb_corpus_analysis.json \
  --output frontend/public/data/dashboard-data.json \
  --view corpus \
  --profile-bank BOB \
  --financials data/psb_financials_dummy.csv \
  --topic-hierarchy data/psb_seed_topics.json
```

Run the frontend locally:

```bash
cd frontend
npm install
npm run dev
```

Then open `http://localhost:3000`.

Frontend routes:

- `/` is the dashboard index.
- `/competitors/` contains only peer comparison views such as overlap matrix, shared topics, top-topic comparison, and comparison parameters.
- `/banks/BOB/`, `/banks/SBI/`, and other generated bank pages contain only individual bank insights such as financials, transcript themes, trends, top topics, and observations.

Create a static production build for Netlify:

```bash
cd frontend
npm install
npm run build
```

The static export is written to `frontend/out`. The root [netlify.toml](netlify.toml) is configured with `base = "frontend"`, `command = "npm run build"`, and `publish = "out"`.

## PSB Corpus Analysis

To reproduce the paper's Section 5.1 and 5.2 style analyses for Indian public sector banks, put the earnings-call transcripts under a folder such as `data/psb_calls/` and create a manifest JSON. Use [psb_manifest.example.json](data/psb_manifest.example.json) as the shape:

```json
[
  {
    "company": "SBI",
    "call_date": "2024-05-09",
    "quarter": "FY24 Q4",
    "path": "psb_calls/SBI_2024-05-09.txt"
  }
]
```

Paths in the manifest are resolved relative to the manifest file. The analysis uses [psb_seed_topics.json](data/psb_seed_topics.json) by default, which contains 10 broad banking topics with 5-6 canonical subtopics under each topic. This keeps the ontology anchored around a topic/subtopic hierarchy while still allowing extracted transcript themes to be grouped back into a compact management view.

Run:

```bash
PYTHONPATH=src python3 -m ects_analysis.corpus \
  --manifest data/psb_manifest.json \
  --output outputs/psb_corpus_analysis.json \
  --exclude-topics data/psb_exclude_topics.example.json \
  --chunk-chars 6000
```

Corpus runs show a progress bar by default; pass `--no-progress` for quiet scripted output.

If OpenRouter returns a request-size or tokens-per-minute error, reduce the chunk size and optionally add a pause between chunk requests:

```bash
PYTHONPATH=src python3 -m ects_analysis.corpus \
  --manifest data/psb_manifest.json \
  --output outputs/psb_corpus_analysis.json \
  --exclude-topics data/psb_exclude_topics.example.json \
  --chunk-chars 3000 \
  --request-delay-seconds 3
```

For local Ollama inference, pass `--provider ollama` and your local model identifier/path:

```bash
PYTHONPATH=src python3 -m ects_analysis.corpus \
  --manifest data/psb_manifest.json \
  --output outputs/psb_corpus_analysis.json \
  --provider ollama \
  --model /path/to/local/model \
  --chunk-chars 3000 \
  --request-delay-seconds 3
```

For direct local Qwen checkpoint inference, use `--provider qwen` and pass the model directory with `--model`:

```bash
PYTHONPATH=src python3 -m ects_analysis.corpus \
  --manifest data/psb_manifest.json \
  --output outputs/psb_corpus_analysis.json \
  --provider qwen \
  --model /path/to/qwen-checkpoint-dir \
  --chunk-chars 3000 \
  --request-delay-seconds 3
```

The output contains:

- `trend_analysis`: per-bank topics that trend up or down across consecutive calls using Kendall's tau, following Section 5.1.
- `competitor_analysis.jaccard_similarity`: pairwise overlap of each bank's top topics, following Section 5.2.
- `competitor_analysis.common_topics`: shared topics for each bank pair with sample excerpts.
- `competitor_analysis.unique_topics`: topics prominent for one bank but absent from peer top-topic sets.

Export the frontend dashboard data:

```bash
PYTHONPATH=src python3 -m ects_analysis.visualize \
  --input outputs/psb_corpus_analysis.json \
  --output frontend/public/data/dashboard-data.json \
  --view corpus \
  --profile-bank BOB \
  --financials data/psb_financials_dummy.csv \
  --topic-hierarchy data/psb_seed_topics.json
```

The React dashboard displays summary metrics, the topic/subtopic hierarchy, a featured bank profile, trend tables, the competitor Jaccard matrix, common topics, unique topics, top topics, and raw topic observations with excerpts. The featured profile defaults to BOB and overlays qualitative transcript summaries with the 3-year dummy financial CSV at [psb_financials_dummy.csv](data/psb_financials_dummy.csv).

To point the profile at another bank or a replacement financial file:

```bash
PYTHONPATH=src python3 -m ects_analysis.visualize \
  --input outputs/psb_corpus_analysis.json \
  --output frontend/public/data/dashboard-data.json \
  --view corpus \
  --profile-bank SBI \
  --financials data/psb_financials_dummy.csv \
  --topic-hierarchy data/psb_seed_topics.json
```
