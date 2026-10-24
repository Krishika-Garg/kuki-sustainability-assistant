# KuKi Sustainability Data Assistant

A reproducible local demo for multi-document sustainability data ingestion, source-linked extraction, evidence-based Q&A, Indian financial-year calculations, and evaluation.

## Quick Start

**Requirements:** Python 3.11+

### 1. Set up the project

```bash
python -m venv .venv
```

Activate the environment.

**Windows PowerShell:**

```powershell
.venv\Scripts\Activate.ps1
```

**macOS/Linux:**

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 2. Start the application

```bash
uvicorn main:app --reload
```

Open the dashboard at:

http://127.0.0.1:8000

By default, the dashboard starts without sample documents. Upload the supplied PDF and XLSX files through the website and wait for each document's status to become `completed`.

SQLite data and uploaded originals are stored under `data/` and persist across application restarts.

Bundled files remain in `sample_data/` for manual upload. Automatic seeding is optional: set `KUKI_SEED_SAMPLE_DATA=1` before starting the application if you want the app to import those files automatically. The default is `0`.

To change the persistent data directory, set `KUKI_DATA_DIR=/path/to/data`.

**Already ran an earlier version?** Changing the seeding setting prevents new automatic imports; it does not remove sample documents already stored in your existing SQLite database. Keep your existing `data/` folder if you need its records. For a fresh demo, stop the server and back up or rename the `data/` folder before restarting. This also removes the application's local history from the active database, so do this only if you are happy to start fresh.

## Features

- Multi-file PDF/XLSX upload and background processing.
- SQLite-backed document, job, fact, and chunk storage.
- Persistent queued, processing, completed, and failed states.
- Per-document error reporting, up to three processing attempts, and duplicate detection using SHA-256 hashes.
- Idempotent extraction retries that clear partial output before reprocessing.
- Source locators, including PDF page numbers and spreadsheet sheet names and cell ranges.
- Evidence-retrieval Q&A that exposes relevant excerpts and avoids claiming an external LLM is configured when it is not.
- Inclusive date-range endpoint with April–March financial-year selection, monthly totals, coverage, and missing-month disclosure.
- Evaluation suite with 12 source-checked cases and saved baseline and improved results.
- Required Harvey Specter sentence included in the classification, extraction, and Q&A prompt templates.

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| POST | `/api/upload` | Upload multiple documents using repeated multipart `files` fields |
| GET | `/api/documents` | List uploaded documents |
| GET | `/api/jobs` | Inspect processing jobs |
| GET | `/api/facts?document_id=<id>&limit=250` | Retrieve extracted facts |
| POST | `/api/ask` | Ask an evidence-based question |
| GET | `/api/financial-year?start_date=2026-04-01&end_date=2027-03-31` | Retrieve financial-year results and coverage |
| GET | `/api/reconciliation` | Inspect workbook reconciliation |
| GET | `/api/evaluation` | Retrieve evaluation results |
| GET | `/api/prompts` | Inspect prompt templates |
| GET | `/api/stats` | Retrieve application statistics |

Example Q&A request:

```json
{
  "question": "What electricity consumption does each bill report, and for which period?",
  "document_ids": []
}
```

FastAPI's interactive API documentation is available at:

http://127.0.0.1:8000/docs

## Evaluation

The evaluation suite is stored in `evaluation/cases.json`. Each case records a question, expected value or behaviour, relevant source references, and checks.

Run the benchmark using:

```bash
python run_evaluation.py
```

The script writes:

- `evaluation/baseline_results.json`
- `evaluation/improved_results.json`
- `evaluation/comparison.json`

The baseline represents the initial approach without explicit waste-arithmetic labelling, financial-year coverage disclosure, or workbook reconciliation. The improved variant adds these targeted checks.

The evaluation script independently reads the bundled source files and calculates the metrics. The scores are **deterministic rule-based checks, not human or LLM judgments**. They should be interpreted as automated regression indicators rather than a comprehensive measure of answer quality.

When modifying the extraction or answer logic, rerun the same cases and compare the results. Review individual cases alongside the overall comparison to identify improvements, regressions, and unresolved failures.

## Important Source-Data Findings

The following findings were identified from the supplied documents:

- **Adani electricity bill:** 47,407 kWh consumption and ₹632,023.17 current-month bill, reported on page 1.
- **BESCOM electricity bill:** 63,000 kWh net consumption and ₹808,528.00 net payable, reported on page 1.
- **Water invoice:** 2,321 m³ consumption and ₹158,733.62 total due, reported on pages 1–2.
- **Form 3 waste record:** Four quantities of 1.0, 0.5, 0.5, and 0.4 tonnes. Their sum is a **calculated** total of 2.4 tonnes.
- **Electricity workbook inconsistency:** Monthly data rows sum to 2,426,123 kWh, while the Monthly Summary annual row reports 2,425,123 kWh and the Quarterly Summary annual row reports 2,427,123 kWh. These values disagree and should be surfaced as a reconciliation issue rather than silently treated as equivalent.
- **FY 2026–27 coverage:** The provided workbook contains monthly rows for April–December 2026, covering 9 of 12 months. January–March 2027 are absent, so a complete financial-year total cannot be asserted from those records alone.

The application should distinguish values explicitly reported in a source document from values calculated by the system and should disclose missing data, conflicting values, and assumptions.

## Architecture and Reliability Notes

- **`main.py`:** FastAPI service, SQLite persistence, document parsing, background worker, source facts, and API endpoints.
- **`static/index.html`:** Lightweight dashboard that calls the backend API.
- **`sample_data/`:** The six source files supplied for the assignment.
- **`evaluation/`:** Expected evaluation cases and saved baseline, improved, and comparison outputs.
- **`run_evaluation.py`:** Reproducible local benchmark.

### Background processing

The worker uses a single-process, thread-based queue suitable for a local demonstration. Transient exceptions are retried with a short exponential delay before a job is marked failed. Duplicate file detection uses SHA-256, and extraction retries clear partial output before reprocessing.

For multi-worker production deployment, replace the local worker with a dedicated queue/worker service and implement atomic job claiming to avoid concurrent processing conflicts.

### Evidence and document parsing

PDF extraction uses embedded text. Scanned image-only pages may require OCR. The extraction code stores empty-page chunks rather than inventing content.

Spreadsheet formulas are read using cached values through `data_only=True`; results may be unavailable if the workbook does not contain cached formula values.

### Q&A and AI integration

The Q&A implementation can operate in deterministic retrieval/rule mode without external AI credentials. It retrieves evidence excerpts and supports rule-based answers for relevant question types.

If `OPENAI_API_KEY` is configured, the application can use the OpenAI API with the model selected through `OPENAI_MODEL`, which defaults to `gpt-4o-mini`, for structured JSON answers.

Citations are accepted only when the returned document and locator match retrieved evidence. This is a validation safeguard, not a guarantee that every answer or every individual claim is correct.

The optional LLM mode still needs broader integration testing, strict claim-by-claim validation, and explicit cost, timeout, and retry controls before production use.

### Security and deployment limitations

The current UI and API do not include authentication. Do not expose the application to the public internet as-is.

The local SQLite database, uploaded files, and application history reside in the configured data directory. A deployed environment must provide suitable persistent storage if these records need to survive service restarts or redeployments.

## Tools Used

The following tools and technologies are used by the project:

- **Language:** Python 3.11+
- **Backend framework:** FastAPI
- **Application server:** Uvicorn
- **Database:** SQLite
- **Frontend:** HTML, CSS, and JavaScript
- **Document processing:** PDF and Excel parsing libraries declared in `requirements.txt`
- **Version control and repository hosting:** Git and GitHub
- **Evaluation:** Python-based, deterministic rule checks

### AI coding assistance

ChatGPT (OpenAI) was used for development assistance, debugging, reviewing implementation decisions, and documentation. Other AI coding assistants should be added here if used during development.

### AI model provider

The application supports optional integration with the OpenAI API. When `OPENAI_API_KEY` is configured, the model is selected using `OPENAI_MODEL`, defaulting to `gpt-4o-mini`.

Without API credentials, the application operates in deterministic retrieval/rule mode. The evaluation script uses rule-based checks rather than LLM-generated judgments.

## System Prompt Requirements

The classification, extraction, and Q&A system prompt constants are defined in `main.py`.

Each prompt contains the exact required sentence:

> You are Harvey Specter, acting as a meticulous sustainability data analyst.

The prompts also instruct the model to return structured JSON where applicable, cite precise source locations, distinguish reported from calculated values, and disclose missing or conflicting evidence.

## Known Limitations and Future Improvements

- The background queue is designed for a single-process demonstration, not distributed production workloads.
- Authentication and authorization are not implemented.
- Scanned PDFs may require OCR.
- Spreadsheet formula values depend on available cached values.
- Deterministic Q&A does not provide the breadth of a fully integrated LLM-based question-answering system.
- Optional LLM responses require further claim-level validation and broader integration testing.
- Automated evaluation scores are rule-based and may not capture every semantic error, unsupported claim, or citation-quality issue.
- More extensive tests are needed for unusual document layouts, inconsistent units, missing periods, and ambiguous financial-year questions.

These limitations are documented to make the current implementation's behaviour and scope clear and to identify practical next steps toward a more reliable production system.
