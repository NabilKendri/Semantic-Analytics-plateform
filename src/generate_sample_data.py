"""
Generates synthetic unstructured text documents (customer support tickets)
to stand in for the 50,000+ real-world files this platform is built to
process. The pipeline itself doesn't care about volume -- run this with a
bigger `n` (or point `data/raw/` at a real corpus) and nothing else changes.
"""

import random
from pathlib import Path

random.seed(7)

CATEGORIES = {
    "billing": [
        "I was charged twice for my subscription this month, order #{oid}. Can you refund the duplicate?",
        "My invoice for order #{oid} shows the wrong amount, please fix it.",
        "I need a receipt for order #{oid} for my accounting department.",
    ],
    "technical": [
        "The app keeps crashing every time I try to open my dashboard after the last update.",
        "Order #{oid}: the API integration stopped returning data since yesterday morning.",
        "Login fails with a 500 error on the mobile app, order #{oid} is affected.",
    ],
    "shipping": [
        "My order #{oid} was supposed to arrive last week and still hasn't shown up.",
        "The package for order #{oid} arrived damaged, I need a replacement.",
        "Tracking for order #{oid} hasn't updated in 5 days, is it lost?",
    ],
    "feedback": [
        "Just wanted to say the new dashboard redesign is fantastic, great work team!",
        "Support was slow to respond but the agent (Marc) was very helpful once we connected.",
        "Not thrilled with the recent pricing change, feels like a lot for what we get.",
    ],
}

URGENCY_PREFIXES = {
    "high": ["URGENT: ", "This is time-sensitive, ", "Need this resolved ASAP - ", ""],
    "normal": ["", "", "Whenever you get a chance, ", ""],
}


def make_document(doc_id: int) -> str:
    category = random.choice(list(CATEGORIES.keys()))
    template = random.choice(CATEGORIES[category])
    oid = random.randint(10000, 99999)
    text = template.format(oid=oid)

    urgency_level = random.choices(["high", "normal"], weights=[0.25, 0.75])[0]
    prefix = random.choice(URGENCY_PREFIXES[urgency_level])

    # occasionally make the document low-quality: truncated, near-empty, or garbled
    quality_roll = random.random()
    if quality_roll < 0.08:
        text = text[: max(10, len(text) // 4)]  # truncated / low-signal
    elif quality_roll < 0.12:
        text = "..."  # near-empty, should get flagged by QA

    return f"{prefix}{text}"


def generate(out_dir: Path, n: int = 200):
    out_dir.mkdir(parents=True, exist_ok=True)
    for i in range(1, n + 1):
        path = out_dir / f"doc_{i:05d}.txt"
        path.write_text(make_document(i))
    print(f"Wrote {n} sample documents to {out_dir}")


if __name__ == "__main__":
    generate(Path("data/raw"), n=200)
