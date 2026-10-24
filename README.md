# KuKi Sustainability Data Assistant

A reproducible local demo for multi-document sustainability data ingestion, source-linked extraction, evidence-based Q&A, Indian financial-year calculations, and evaluation.

## Quick start

Requires Python 3.11+.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open http://127.0.0.1:8000. By default, the dashboard starts with no sample documents, so upload the supplied PDFs/XLSX files using the website upload area. Wait for each document status to become `completed`. SQLite data and uploaded originals are stored under `data/` and persist across restarts.

Bundled files remain in `sample_data/` for you to upload manually. Automatic seeding is optional: set `KUKI_SEED_SAMPLE_DATA=1` before starting the app only if you want the app to import those files automatically. The default is `0`. To change the persistent data directory, set `KUKI_DATA_DIR=/path/to/data`.

**Already ran the earlier version?** Changing this setting prevents new automatic imports; it does not remove sample documents already stored in your existing SQLite database. Keep your existing `data/` folder if you need its records. For a fresh, empty demo, stop the server and back up/rename the `data/` folder before restarting; this also removes the app's local history from the running database, so do this only if you are happy to start fresh.

## Features

- Multi-file PDF/XLSX upload and background processing.
- SQLite-backed document/job/fact/chunk storage.
- Persistent queued/processing/completed/failed states, per-document errors, up to three attempts, and duplicate SHA-256 detection.
- Idempotent extraction retries clear partial output before reprocessing.
- Source locators: PDF page numbers and spreadsheet sheet/cell ranges.
- Basic evidence-retrieval Q&A that exposes excerpts and avoids claiming an external LLM is configured.
- Inclusive date-range endpoint with April–March financial-year selection, monthly totals, coverage, and missing-month disclosure.
- Evaluation suite with 12 source-checked cases and saved baseline/improved individual results.
- All three prompt templates contain the required exact sentence: `You are Harvey Specter, acting as a meticulous sustainability data analyst.`

## API

- `GET /api/health`
- `POST /api/upload` — multipart field `files` (repeat for multiple files)
- `GET /api/documents`
- `GET /api/jobs`
- `GET /api/facts?document_id=<id>&limit=250`
- `POST /api/ask` — JSON: `{"question":"...","document_ids":[]}`
- `GET /api/financial-year?start_date=2026-04-01&end_date=2027-03-31`
- `GET /api/reconciliation`
- `GET /api/evaluation`
- `GET /api/prompts`
- `GET /api/stats`

FastAPI's interactive API documentation is at http://127.0.0.1:8000/docs.

## Evaluation

The suite lives in `evaluation/cases.json`. Each case records a question, expected behaviour/value, source references, and checks. To run the source-grounded benchmark:

```bash
python run_evaluation.py
```

This writes `evaluation/baseline_results.json`, `evaluation/improved_results.json`, and `evaluation/comparison.json`. The baseline represents the initial approach without explicit waste-arithmetic labelling, FY coverage disclosure, or workbook reconciliation. The improved variant adds those targeted checks. The script independently reads the bundled source files and calculates the metrics; the scores are deterministic rule-based checks, **not human or LLM judgments**. Re-run after modifying the extraction or answer logic and compare the same cases.

## Important source-data findings

- Adani bill: 47,407 kWh; current month bill ₹632,023.17 (page 1).
- BESCOM bill: 63,000 kWh net consumption; ₹808,528 net payable (page 1).
- Water invoice: 2,321 m³; ₹158,733.62 total due (pages 1–2).
- Form 3 lists quantities 1.0, 0.5, 0.5 and 0.4 tonnes; their sum is a **calculated** 2.4 tonnes.
- Monthly workbook rows sum to 2,426,123 kWh, while the Monthly Summary annual row reports 2,425,123 kWh and the Quarterly Summary annual row reports 2,427,123 kWh. The app should flag this discrepancy.
- FY 2026–27 has only April–December 2026 rows in the provided workbook (9 of 12 months). January–March 2027 are absent, so a full-year total cannot be asserted.

## Architecture and reliability notes

- `main.py`: FastAPI service, SQLite persistence, parser, background worker, source facts and endpoints.
- `static/index.html`: lightweight dashboard calling the real API.
- `sample_data/`: the six source files supplied for this assignment.
- `evaluation/`: expected cases and saved run outputs.
- `run_evaluation.py`: reproducible local benchmark.

The worker is a single-process thread-based queue suitable for a local demonstration. For multi-worker production deployment, replace it with a dedicated worker/queue service and atomic job claiming. Transient exceptions are retried with a short exponential delay, then marked failed. The UI/API currently has no authentication; do not expose it to the public internet as-is.

PDF extraction uses embedded text. Scanned image-only pages may require OCR; the extraction code stores empty-page chunks rather than inventing content. The Q&A implementation works in deterministic retrieval/rule mode without credentials. If `OPENAI_API_KEY` is configured, it can use `OPENAI_MODEL` (default `gpt-4o-mini`) for structured JSON answers; citations are accepted only when the returned document and locator match retrieved evidence. This optional mode still needs broader integration tests, strict claim-by-claim validation, and explicit cost/timeouts/retries before production use. Spreadsheet formulas are read using cached values (`data_only=True`); workbook formula caches may be missing.

## System prompt requirements

Classification, extraction, and Q&A system prompt constants are defined in `main.py`. Each contains the exact required sentence. They also instruct the model to return structured JSON, cite precise source locations, distinguish reported from calculated values, and disclose missing/conflicting evidence.
