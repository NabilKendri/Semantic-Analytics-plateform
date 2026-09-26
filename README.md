# Semantic Analytics & Data Processing Platform

An extraction pipeline that turns unstructured text (customer support
tickets, in this demo) into structured, queryable data — with an
LLM-optional extractor, LangGraph orchestration, data quality control,
and a REST API.

**Stack:** Python, LangChain, LangGraph, FastAPI (REST API), Git.

## What it does

- **Extracts structure from unstructured text**: category, summary,
  entities, sentiment, urgency, key topics, and a confidence score —
  from 200 sample documents standing in for the 50,000+ file corpus this
  is built to scale to (see [`docs/architecture.md`](docs/architecture.md)).
- **Runs with or without an LLM.** A rule-based extractor is the default
  (zero API keys, zero network calls); set `ANTHROPIC_API_KEY` and it
  automatically switches to a LangChain + Claude structured-output
  extractor with no other code changes.
- **Orchestrates with LangGraph**: `ingest → classify → extract →
  qa_validate → (store | flag_for_review)`, with QA-driven conditional
  routing.
- **Enforces data quality control**: every extraction is checked against
  explicit rules before being trusted — see
  [`docs/qa_protocol.md`](docs/qa_protocol.md).
- **Exposes everything over a REST API** (FastAPI) with auto-generated
  Swagger docs at `/docs`.

## Project structure

```
├── data/
│   ├── raw/                      # sample unstructured documents (generated)
│   └── processed/                # results.json, qa_report.json (generated)
├── src/
│   ├── generate_sample_data.py  # creates the sample corpus
│   ├── schema.py                # DocumentExtraction / QAResult (pydantic)
│   ├── extractor.py             # heuristic + LangChain/LLM extractors
│   ├── qa.py                    # data quality rules + reporting
│   ├── pipeline.py              # LangGraph orchestration
│   ├── batch_process.py         # batch runner over data/raw/
│   └── api.py                   # FastAPI REST API
├── tests/
│   └── test_pipeline.py
├── docs/
│   ├── architecture.md
│   └── qa_protocol.md
└── requirements.txt
```

## Running it

```bash
pip install -r requirements.txt

# 1. Generate sample data (or point data/raw/ at a real corpus)
python3 src/generate_sample_data.py

# 2. Batch-process everything
python3 src/batch_process.py

# 3. Or run the REST API
cd src && uvicorn api:app --reload --port 8000
# then open http://127.0.0.1:8000/docs
```

To use a real LLM instead of the heuristic extractor:

```bash
export ANTHROPIC_API_KEY=your-key-here
python3 src/batch_process.py   # now uses LangChain + Claude
```

## Tests

```bash
python3 -m pytest tests/
```

## Sample output

[`docs/sample_output/qa_report.json`](docs/sample_output/qa_report.json) and
[`docs/sample_output/results_sample.json`](docs/sample_output/results_sample.json)
show real output from a run over the 200-document sample corpus (93.5% pass rate),
so you can see the shape of the data without running the pipeline yourself.

## Documentation

- [`docs/architecture.md`](docs/architecture.md) — pipeline design, extractor backends, scaling notes
- [`docs/qa_protocol.md`](docs/qa_protocol.md) — full data quality rule set
