"""
REST API for the platform.

Endpoints:
  POST /documents           -> submit one document, get its structured result back
  GET  /documents           -> list processed results (filter by category/status)
  GET  /documents/{doc_id}  -> get one result
  POST /batch/process       -> run the pipeline over data/raw/ and persist results
  GET  /qa/report           -> latest aggregate QA report
  GET  /health              -> liveness check

Run: uvicorn api:app --reload --port 8000
Docs auto-generated at /docs (Swagger UI) and /redoc.
"""

import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from pipeline import run_pipeline
from batch_process import process_folder
from qa import build_qa_report
from schema import QAResult

app = FastAPI(
    title="Semantic Analytics & Data Processing Platform",
    description="Extraction pipeline for unstructured documents, with QA validation.",
    version="1.0.0",
)

ROOT = Path(__file__).parent.parent
PROCESSED_DIR = ROOT / "data" / "processed"
RAW_DIR = ROOT / "data" / "raw"

# In-memory index of results for this API process, seeded from disk if present.
_results_store: dict[str, dict] = {}


def _load_from_disk():
    results_path = PROCESSED_DIR / "results.json"
    if results_path.exists():
        for r in json.loads(results_path.read_text()):
            _results_store[r["document_id"]] = r


_load_from_disk()


class DocumentIn(BaseModel):
    document_id: str
    text: str


@app.get("/health")
def health():
    return {"status": "ok", "documents_indexed": len(_results_store)}


@app.post("/documents")
def submit_document(doc: DocumentIn):
    state = run_pipeline(document_id=doc.document_id, raw_text=doc.text)
    record = {
        "document_id": state["document_id"],
        "status": state["status"],
        "extraction": state["extraction"].model_dump(),
        "qa_issues": state["qa_result"].issues,
    }
    _results_store[doc.document_id] = record
    return record


@app.get("/documents")
def list_documents(
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None, description="'stored' or 'flagged'"),
    limit: int = Query(50, le=500),
):
    items = list(_results_store.values())
    if category:
        items = [r for r in items if r["extraction"]["category"] == category]
    if status:
        items = [r for r in items if r["status"] == status]
    return {"count": len(items), "results": items[:limit]}


@app.get("/documents/{document_id}")
def get_document(document_id: str):
    record = _results_store.get(document_id)
    if not record:
        raise HTTPException(status_code=404, detail="document not found")
    return record


@app.post("/batch/process")
def batch_process():
    if not RAW_DIR.exists():
        raise HTTPException(status_code=400, detail=f"{RAW_DIR} does not exist")
    results = process_folder(RAW_DIR)
    for r in results:
        _results_store[r["document_id"]] = r

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    (PROCESSED_DIR / "results.json").write_text(json.dumps(results, indent=2))

    qa_objs = [QAResult(document_id=r["document_id"], passed=r["status"] == "stored", issues=r["qa_issues"])
               for r in results]
    report = build_qa_report(qa_objs)
    (PROCESSED_DIR / "qa_report.json").write_text(json.dumps(report, indent=2))

    return {"processed": len(results), "qa_report": report}


@app.get("/qa/report")
def qa_report():
    report_path = PROCESSED_DIR / "qa_report.json"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="no QA report yet -- run /batch/process first")
    return json.loads(report_path.read_text())
