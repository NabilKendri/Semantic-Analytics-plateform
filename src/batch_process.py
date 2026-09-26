"""
Runs every file in data/raw/ through the pipeline and writes:
- data/processed/results.json  (all extractions + statuses)
- data/processed/qa_report.json (aggregate QA stats)

This is the "extraction pipeline to structure and analyze unstructured
data files" bullet at batch scale. Swap data/raw/ for a real corpus and
bump the loop -- nothing else in this script changes at 50,000 files.
"""

import json
from pathlib import Path

from pipeline import run_pipeline
from qa import build_qa_report


def process_folder(raw_dir: Path) -> list[dict]:
    results = []
    for path in sorted(raw_dir.glob("*.txt")):
        text = path.read_text()
        state = run_pipeline(document_id=path.stem, raw_text=text)
        results.append({
            "document_id": state["document_id"],
            "status": state["status"],
            "extraction": state["extraction"].model_dump(),
            "qa_issues": state["qa_result"].issues,
        })
    return results


def main():
    root = Path(__file__).parent.parent
    raw_dir = root / "data" / "raw"
    processed_dir = root / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    print(f"Processing files in {raw_dir}...")
    results = process_folder(raw_dir)
    print(f"  {len(results)} documents processed")

    stored = sum(1 for r in results if r["status"] == "stored")
    flagged = len(results) - stored
    print(f"  {stored} stored, {flagged} flagged for review")

    results_path = processed_dir / "results.json"
    results_path.write_text(json.dumps(results, indent=2))
    print(f"  Results written to {results_path}")

    from schema import QAResult
    qa_objs = [QAResult(document_id=r["document_id"], passed=r["status"] == "stored", issues=r["qa_issues"])
               for r in results]
    report = build_qa_report(qa_objs)
    report_path = processed_dir / "qa_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"  QA report written to {report_path}")
    print(f"  Pass rate: {report['pass_rate']:.1%}")


if __name__ == "__main__":
    main()
