import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, text
from db.models import Dataset
from core.search.fuzzy_search import rank_results, normalize_query
from core.ai.openai_service import get_embedding
import json

logger = logging.getLogger(__name__)

# Search fields to check across datasets
SEARCH_FIELDS = ["name", "username", "email", "phone", "description", "tags", "value"]


async def search_in_db(session: AsyncSession, query: str, mode: str = "standard") -> list[dict]:
    """
    Main search function. Searches across all active datasets.
    In production, this queries actual dataset tables.
    Here we demonstrate the pattern with a mock + fuzzy ranking.
    """
    q = normalize_query(query)
    results = []

    try:
        # Get active datasets
        ds_result = await session.execute(
            select(Dataset).where(Dataset.is_active == True)
        )
        datasets = ds_result.scalars().all()

        for dataset in datasets:
            # In production: dynamically query dataset-specific tables
            # Here we use a generic full-text search pattern
            try:
                raw = await _search_dataset(session, dataset, q, mode)
                results.extend(raw)
            except Exception as e:
                logger.warning(f"Dataset {dataset.name} search error: {e}")

    except Exception as e:
        logger.error(f"Search error: {e}")

    # Fuzzy rank all results
    if results:
        results = rank_results(query, results, SEARCH_FIELDS)

    # Deep/Ultra: semantic re-ranking
    if mode in ("deep", "ultra") and results:
        results = await _semantic_rerank(query, results)

    return results[:50]  # cap at 50


async def _search_dataset(
    session: AsyncSession, dataset: Dataset, query: str, mode: str
) -> list[dict]:
    """Search within a specific dataset using pg full-text search."""
    # Generic search on a hypothetical 'records' table per dataset
    # In real deployment, each dataset has its own table/schema
    try:
        sql = text("""
            SELECT id, data, ts_rank(to_tsvector('english', data::text),
                   plainto_tsquery('english', :q)) AS rank
            FROM dataset_records
            WHERE dataset_id = :ds_id
              AND to_tsvector('english', data::text) @@ plainto_tsquery('english', :q)
            ORDER BY rank DESC
            LIMIT 20
        """)
        result = await session.execute(sql, {"q": query, "ds_id": dataset.id})
        rows = result.fetchall()
        records = []
        for row in rows:
            data = row.data if isinstance(row.data, dict) else json.loads(row.data)
            data["_dataset"] = dataset.name
            data["_rank"] = float(row.rank)
            records.append(data)
        return records
    except Exception:
        return []


async def _semantic_rerank(query: str, results: list[dict]) -> list[dict]:
    """Re-rank results using embedding similarity."""
    try:
        query_embedding = await get_embedding(query)
        if not query_embedding:
            return results

        for record in results:
            text_repr = " ".join(str(v) for v in record.values() if isinstance(v, str))
            rec_embedding = await get_embedding(text_repr[:500])
            if rec_embedding:
                similarity = _cosine_similarity(query_embedding, rec_embedding)
                record["_semantic_score"] = round(similarity, 3)
            else:
                record["_semantic_score"] = 0.0

        return sorted(results, key=lambda x: x.get("_semantic_score", 0), reverse=True)
    except Exception as e:
        logger.warning(f"Semantic rerank error: {e}")
        return results


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x ** 2 for x in a) ** 0.5
    norm_b = sum(x ** 2 for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
