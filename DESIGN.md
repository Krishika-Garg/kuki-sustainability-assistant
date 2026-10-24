# Design and improvement note

## Design
The demo uses FastAPI with SQLite and a background worker. Original files are persisted, jobs survive application restarts, file hashes prevent duplicate ingestion, and per-document failures are isolated. PDF evidence uses page locators; workbook evidence uses sheet and cell-range locators. A small web dashboard consumes the same API endpoints used by the demo.

## Targeted improvement
The initial baseline was weak at handling cross-row and cross-sheet logic. The targeted improvement added:
1. FY-aware month selection and explicit missing-month reporting for April–March years.
2. A reconciliation endpoint comparing summed monthly rows with reported annual totals in the Monthly Summary, Quarterly Summary, and Source-wise Annual Analysis.
3. Explicit labelling of arithmetic derived from hazardous-waste quantities.
4. Evidence-locator validation for optional LLM answers.

## Evaluation result
Run `python run_evaluation.py` to reproduce the benchmark. In the current deterministic suite, mean case score moved from 0.8612 to 1.0000 and fully passing cases moved from 9/12 to 12/12. These are deterministic rule-based checks against the supplied data, not human or LLM quality judgments.

## Limitations
The queue is a single-process worker thread, not a distributed queue. Scanned image-only PDFs may need OCR. The default Q&A path is retrieval/rules rather than a generative model; OpenAI mode is optional and requires an API key. The evaluation suite is compact and should be expanded with adversarial, ambiguous, and out-of-scope questions. Authentication and production deployment hardening are not included.
