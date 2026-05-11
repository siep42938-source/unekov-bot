from rapidfuzz import fuzz, process
from typing import Any
import re


def normalize_query(query: str) -> str:
    """Normalize search query."""
    query = query.strip().lower()
    query = re.sub(r"[^\w\s@._-]", "", query)
    return query


def fuzzy_match(query: str, candidates: list[str], threshold: int = 70) -> list[tuple[str, float]]:
    """Return candidates matching query above threshold."""
    results = process.extract(query, candidates, scorer=fuzz.WRatio, limit=10)
    return [(match, score / 100.0) for match, score, _ in results if score >= threshold]


def score_record(query: str, record: dict, fields: list[str]) -> float:
    """Score a record against a query across multiple fields."""
    scores = []
    q = normalize_query(query)
    for field in fields:
        value = str(record.get(field, "")).lower()
        if not value:
            continue
        # Exact match
        if q in value or value in q:
            scores.append(1.0)
            continue
        # Fuzzy
        score = fuzz.WRatio(q, value) / 100.0
        scores.append(score)
    return max(scores) if scores else 0.0


def rank_results(query: str, records: list[dict], search_fields: list[str]) -> list[dict]:
    """Rank records by relevance to query."""
    scored = []
    for record in records:
        score = score_record(query, record, search_fields)
        if score > 0.4:
            scored.append({**record, "_score": round(score, 3)})
    return sorted(scored, key=lambda x: x["_score"], reverse=True)
