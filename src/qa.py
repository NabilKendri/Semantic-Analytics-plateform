"""
Data quality control protocol: rules an extraction must pass before it's
trusted enough to store as "clean". Failing rows are flagged for review
instead of silently accepted or dropped.

See docs/qa_protocol.md for the rationale behind each rule.
"""

from schema import DocumentExtraction, QAResult

MIN_CONFIDENCE = 0.5
MIN_SUMMARY_LENGTH = 8
PLACEHOLDER_SUMMARIES = {"(insufficient content to summarize)", ""}


def validate(extraction: DocumentExtraction) -> QAResult:
    issues = []

    if extraction.confidence < MIN_CONFIDENCE:
        issues.append(f"low_confidence ({extraction.confidence})")

    if extraction.summary.strip() in PLACEHOLDER_SUMMARIES or len(extraction.summary.strip()) < MIN_SUMMARY_LENGTH:
        issues.append("summary_too_short_or_missing")

    if extraction.category == "other":
        issues.append("category_unresolved")

    if not extraction.key_topics and extraction.category != "feedback":
        issues.append("no_key_topics_extracted")

    return QAResult(document_id=extraction.document_id, passed=len(issues) == 0, issues=issues)


def build_qa_report(qa_results: list[QAResult]) -> dict:
    total = len(qa_results)
    passed = sum(1 for r in qa_results if r.passed)
    failed = total - passed

    issue_counts: dict[str, int] = {}
    for r in qa_results:
        for issue in r.issues:
            key = issue.split(" (")[0]  # strip variable part like "(0.3)"
            issue_counts[key] = issue_counts.get(key, 0) + 1

    return {
        "total_documents": total,
        "passed": passed,
        "flagged": failed,
        "pass_rate": round(passed / total, 4) if total else 0,
        "issue_breakdown": dict(sorted(issue_counts.items(), key=lambda x: -x[1])),
    }
