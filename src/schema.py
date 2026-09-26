"""
The structured record every raw document gets turned into. Used both as
the LangChain structured-output target (when an LLM backend is active)
and as the QA validation schema.
"""

from typing import Literal
from pydantic import BaseModel, Field


class DocumentExtraction(BaseModel):
    document_id: str
    category: Literal["billing", "technical", "shipping", "feedback", "other"] = Field(
        description="Primary topic of the document"
    )
    summary: str = Field(description="One-sentence summary of the document's content")
    entities: list[str] = Field(
        default_factory=list, description="Named entities found (order IDs, names, products)"
    )
    sentiment: Literal["positive", "neutral", "negative"] = Field(
        description="Overall sentiment expressed in the document"
    )
    urgency: Literal["high", "normal"] = Field(description="Urgency level")
    key_topics: list[str] = Field(default_factory=list, description="Key topics/keywords")
    confidence: float = Field(ge=0.0, le=1.0, description="Extractor's confidence in this result")


class QAResult(BaseModel):
    document_id: str
    passed: bool
    issues: list[str] = Field(default_factory=list)
