"""
FileScanner — поиск совпадений в загруженных файлах (CSV, JSON, TXT).
Ищет по всем колонкам, возвращает строки с совпадениями и score.
"""
import csv
import json
import io
import logging
from pathlib import Path
from core.search.fuzzy_search import normalize_query, score_record

logger = logging.getLogger(__name__)

MAX_ROWS = 50_000   # защита от огромных файлов


def scan_csv(file_path: str, query: str, threshold: float = 0.5) -> list[dict]:
    q = normalize_query(query)
    results = []
    try:
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            fields = reader.fieldnames or []
            for i, row in enumerate(reader):
                if i > MAX_ROWS:
                    break
                score = score_record(q, dict(row), fields)
                if score >= threshold:
                    results.append({**row, "_score": round(score, 3), "_source_file": Path(file_path).name})
    except Exception as e:
        logger.error(f"CSV scan error {file_path}: {e}")
    return sorted(results, key=lambda x: x["_score"], reverse=True)[:50]


def scan_json(file_path: str, query: str, threshold: float = 0.5) -> list[dict]:
    q = normalize_query(query)
    results = []
    try:
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            return []
        for i, item in enumerate(data):
            if i > MAX_ROWS:
                break
            if not isinstance(item, dict):
                item = {"value": str(item)}
            fields = list(item.keys())
            score = score_record(q, item, fields)
            if score >= threshold:
                results.append({**item, "_score": round(score, 3), "_source_file": Path(file_path).name})
    except Exception as e:
        logger.error(f"JSON scan error {file_path}: {e}")
    return sorted(results, key=lambda x: x["_score"], reverse=True)[:50]


def scan_txt(file_path: str, query: str, threshold: float = 0.5) -> list[dict]:
    from rapidfuzz import fuzz
    q = normalize_query(query)
    results = []
    try:
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            for i, line in enumerate(f):
                if i > MAX_ROWS:
                    break
                line = line.strip()
                if not line:
                    continue
                score = fuzz.WRatio(q, line.lower()) / 100.0
                if score >= threshold:
                    results.append({
                        "line": i + 1,
                        "content": line,
                        "_score": round(score, 3),
                        "_source_file": Path(file_path).name,
                    })
    except Exception as e:
        logger.error(f"TXT scan error {file_path}: {e}")
    return sorted(results, key=lambda x: x["_score"], reverse=True)[:50]


def scan_file(file_path: str, query: str, threshold: float = 0.5) -> list[dict]:
    """Auto-detect file type and scan."""
    ext = Path(file_path).suffix.lower()
    if ext == ".csv":
        return scan_csv(file_path, query, threshold)
    elif ext == ".json":
        return scan_json(file_path, query, threshold)
    elif ext in (".txt", ".log", ".tsv"):
        return scan_txt(file_path, query, threshold)
    else:
        logger.warning(f"Unsupported file type: {ext}")
        return []
