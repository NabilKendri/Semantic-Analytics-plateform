"""
Basic tests for the extractor, QA rules, and pipeline routing.
Run: pytest tests/ (from the project root, with src/ on PYTHONPATH)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from extractor import HeuristicExtractor
from qa import validate, MIN_CONFIDENCE
from pipeline import run_pipeline


def test_extractor_detects_shipping_category():
    result = HeuristicExtractor().extract("t1", "My order #12345 arrived damaged.")
    assert result.category == "shipping"
    assert "#12345" in result.entities


def test_extractor_detects_urgency():
    result = HeuristicExtractor().extract("t2", "URGENT: need this fixed ASAP.")
    assert result.urgency == "high"


def test_extractor_low_content_gets_low_confidence():
    result = HeuristicExtractor().extract("t3", "...")
    assert result.confidence < MIN_CONFIDENCE


def test_qa_flags_low_confidence():
    result = HeuristicExtractor().extract("t4", "...")
    qa = validate(result)
    assert not qa.passed
    assert any("low_confidence" in issue for issue in qa.issues)


def test_qa_passes_clean_extraction():
    result = HeuristicExtractor().extract("t5", "My order #99999 was damaged, need a replacement please.")
    qa = validate(result)
    assert qa.passed


def test_pipeline_routes_flagged_documents_correctly():
    state = run_pipeline("t6", "...")
    assert state["status"] == "flagged"


def test_pipeline_routes_clean_documents_correctly():
    state = run_pipeline("t7", "My order #11111 arrived damaged, need a replacement.")
    assert state["status"] == "stored"
