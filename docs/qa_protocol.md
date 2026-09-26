# Data Quality Control (QA) Protocol

Every extraction produced by the pipeline is validated against explicit,
codified rules (`src/qa.py`) before being accepted as "clean." An
extraction that fails any rule is **flagged for review**, not discarded
and not silently accepted — a human (or a stronger backend) should look
at it before it's treated as ground truth.

## Rules

| Rule | Condition | Rationale |
|---|---|---|
| `low_confidence` | `confidence < 0.5` | The extractor itself is signalling uncertainty — usually short, ambiguous, or off-template input. |
| `summary_too_short_or_missing` | summary is a placeholder or under 8 characters | A missing summary means downstream consumers (dashboards, search) have nothing useful to show. |
| `category_unresolved` | category resolved to `"other"` | No category-specific keywords/signal matched anything — likely needs a human category or a schema update. |
| `no_key_topics_extracted` | zero topics found (except `feedback`, which is often topic-free praise/complaints) | No topics usually means the document didn't match anything the extractor knows about yet. |

## Aggregate reporting

`build_qa_report()` produces:

```json
{
  "total_documents": 200,
  "passed": 187,
  "flagged": 13,
  "pass_rate": 0.935,
  "issue_breakdown": {
    "low_confidence": 13,
    "category_unresolved": 13,
    "no_key_topics_extracted": 13,
    "summary_too_short_or_missing": 6
  }
}
```

`issue_breakdown` is what you'd actually act on operationally: a spike in
one issue type points at a specific fix (e.g. a new category needed, or a
prompt/rule change), rather than just "quality dropped."

## Extending the protocol

Add a rule by adding a check in `validate()` and appending to `issues` —
`build_qa_report()` automatically picks up any new issue string in its
breakdown with no changes needed there.
