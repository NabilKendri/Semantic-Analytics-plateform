"""
Extracts structured data from a raw document.

Two backends, same interface:
- LLMExtractor: LangChain + an Anthropic chat model with structured output.
  Used automatically if ANTHROPIC_API_KEY is set.
- HeuristicExtractor: keyword/regex rules. No API key or network needed --
  this is what runs by default so the whole platform works out of the box,
  and is also what the QA layer benchmarks the LLM backend against.

get_extractor() picks the right one at runtime.
"""

import os
import re
from abc import ABC, abstractmethod

from schema import DocumentExtraction

CATEGORY_KEYWORDS = {
    "billing": ["charge", "invoice", "refund", "receipt", "payment", "subscription"],
    "technical": ["crash", "error", "bug", "api", "login", "500", "integration"],
    "shipping": ["order", "package", "tracking", "arrive", "deliver", "shipment"],
    "feedback": ["great", "fantastic", "thrilled", "helpful", "team", "pricing", "redesign"],
}

POSITIVE_WORDS = ["great", "fantastic", "helpful", "thanks", "good", "love", "excellent"]
NEGATIVE_WORDS = ["crash", "error", "damaged", "lost", "slow", "not thrilled", "wrong", "urgent", "asap"]
URGENCY_WORDS = ["urgent", "asap", "immediately", "time-sensitive", "time sensitive", "critical"]

ORDER_ID_RE = re.compile(r"#\d{4,6}")
NAME_RE = re.compile(r"\b[A-Z][a-z]{2,}\b")
COMMON_WORDS = {"The", "This", "My", "Just", "Support", "Need", "Login", "Order", "Not", "URGENT"}


class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, document_id: str, text: str) -> DocumentExtraction:
        ...


class HeuristicExtractor(BaseExtractor):
    """Rule-based extraction. Deterministic, fast, zero external dependencies."""

    def extract(self, document_id: str, text: str) -> DocumentExtraction:
        text_lower = text.lower()
        stripped = text.strip()

        if len(stripped) < 5:
            return DocumentExtraction(
                document_id=document_id,
                category="other",
                summary="(insufficient content to summarize)",
                entities=[],
                sentiment="neutral",
                urgency="normal",
                key_topics=[],
                confidence=0.1,
            )

        # Category: score each category by keyword hits, pick the max
        scores = {
            cat: sum(1 for kw in kws if kw in text_lower)
            for cat, kws in CATEGORY_KEYWORDS.items()
        }
        best_category = max(scores, key=scores.get)
        category = best_category if scores[best_category] > 0 else "other"

        # Sentiment
        pos_hits = sum(1 for w in POSITIVE_WORDS if w in text_lower)
        neg_hits = sum(1 for w in NEGATIVE_WORDS if w in text_lower)
        if neg_hits > pos_hits:
            sentiment = "negative"
        elif pos_hits > neg_hits:
            sentiment = "positive"
        else:
            sentiment = "neutral"

        # Urgency
        urgency = "high" if any(w in text_lower for w in URGENCY_WORDS) else "normal"

        # Entities: order IDs + capitalized proper-noun-looking words
        order_ids = ORDER_ID_RE.findall(text)
        names = [w for w in NAME_RE.findall(stripped) if w not in COMMON_WORDS]
        entities = list(dict.fromkeys(order_ids + names))  # dedupe, keep order

        # Key topics: matched keywords across all categories
        key_topics = [kw for kws in CATEGORY_KEYWORDS.values() for kw in kws if kw in text_lower]

        # Summary: first sentence, or truncate
        first_sentence = re.split(r"(?<=[.!?])\s", stripped)[0]
        summary = first_sentence if len(first_sentence) < 160 else first_sentence[:157] + "..."

        # Confidence: longer, keyword-rich, unambiguous documents score higher
        confidence = min(1.0, 0.4 + 0.05 * scores[best_category] + min(len(stripped) / 200, 0.3))
        if category == "other":
            confidence *= 0.5

        return DocumentExtraction(
            document_id=document_id,
            category=category,
            summary=summary,
            entities=entities[:10],
            sentiment=sentiment,
            urgency=urgency,
            key_topics=list(dict.fromkeys(key_topics))[:8],
            confidence=round(confidence, 2),
        )


class LLMExtractor(BaseExtractor):
    """LangChain + an Anthropic chat model, using structured output to fill
    the same DocumentExtraction schema. Requires ANTHROPIC_API_KEY."""

    def __init__(self, model: str = "claude-sonnet-4-6"):
        from langchain_anthropic import ChatAnthropic
        from langchain_core.prompts import ChatPromptTemplate

        llm = ChatAnthropic(model=model, temperature=0)
        self.structured_llm = llm.with_structured_output(DocumentExtraction)
        self.prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You extract structured data from customer support documents. "
             "Fill every field of the schema based only on the document text."),
            ("human", "document_id: {document_id}\n\nDocument:\n{text}"),
        ])

    def extract(self, document_id: str, text: str) -> DocumentExtraction:
        chain = self.prompt | self.structured_llm
        result = chain.invoke({"document_id": document_id, "text": text})
        result.document_id = document_id  # guard against the model altering it
        return result


def get_extractor() -> BaseExtractor:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return LLMExtractor()
    return HeuristicExtractor()
