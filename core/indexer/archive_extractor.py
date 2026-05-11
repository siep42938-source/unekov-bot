"""
ArchiveExtractor — распаковывает RAR, ZIP, 7z архивы
и индексирует содержимое (TXT, CSV, JSON, PY файлы).
"""
import os
import logging
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_ARCHIVES = {".rar", ".zip", ".7z", ".gz", ".tar"}
INDEXABLE_EXTENSIONS = {".txt", ".csv", ".json", ".py", ".log", ".sql"}
MAX_EXTRACT_SIZE = 50 * 1024 * 1024  # 50 MB


def extract_archive(archive_path: str, dest_dir: str) -> list[str]:
    """
    Распаковывает архив в dest_dir.
    Возвращает список путей к извлечённым файлам.
    """
    ext = Path(archive_path).suffix.lower()
    extracted = []

    try:
        if ext == ".zip":
            extracted = _extract_zip(archive_path, dest_dir)
        elif ext == ".rar":
            extracted = _extract_rar(archive_path, dest_dir)
        elif ext == ".7z":
            extracted = _extract_7z(archive_path, dest_dir)
        elif ext in (".tar", ".gz"):
            extracted = _extract_tar(archive_path, dest_dir)
    except Exception as e:
        logger.error(f"Extract error {archive_path}: {e}")

    return extracted


def _extract_zip(path: str, dest: str) -> list[str]:
    import zipfile
    files = []
    with zipfile.ZipFile(path, "r") as zf:
        for member in zf.infolist():
            if member.file_size > MAX_EXTRACT_SIZE:
                continue
            ext = Path(member.filename).suffix.lower()
            if ext in INDEXABLE_EXTENSIONS:
                try:
                    zf.extract(member, dest)
                    files.append(os.path.join(dest, member.filename))
                except Exception:
                    pass
    return files


def _extract_rar(path: str, dest: str) -> list[str]:
    files = []
    try:
        import rarfile
        with rarfile.RarFile(path) as rf:
            for member in rf.infolist():
                ext = Path(member.filename).suffix.lower()
                if ext in INDEXABLE_EXTENSIONS:
                    try:
                        rf.extract(member, dest)
                        files.append(os.path.join(dest, member.filename))
                    except Exception:
                        pass
    except ImportError:
        # Fallback: попробуем через subprocess unrar
        try:
            import subprocess
            result = subprocess.run(
                ["unrar", "e", "-y", path, dest],
                capture_output=True, timeout=30
            )
            if result.returncode == 0:
                for f in os.listdir(dest):
                    if Path(f).suffix.lower() in INDEXABLE_EXTENSIONS:
                        files.append(os.path.join(dest, f))
        except Exception as e:
            logger.warning(f"RAR extract failed (install rarfile or unrar): {e}")
    return files


def _extract_7z(path: str, dest: str) -> list[str]:
    files = []
    try:
        import py7zr
        with py7zr.SevenZipFile(path, mode="r") as z:
            all_files = z.getnames()
            targets = [f for f in all_files if Path(f).suffix.lower() in INDEXABLE_EXTENSIONS]
            if targets:
                z.extract(dest, targets=targets)
                for f in targets:
                    files.append(os.path.join(dest, f))
    except ImportError:
        logger.warning("py7zr not installed, skipping .7z files. pip install py7zr")
    return files


def _extract_tar(path: str, dest: str) -> list[str]:
    import tarfile
    files = []
    with tarfile.open(path) as tf:
        for member in tf.getmembers():
            if not member.isfile():
                continue
            ext = Path(member.name).suffix.lower()
            if ext in INDEXABLE_EXTENSIONS and member.size < MAX_EXTRACT_SIZE:
                try:
                    tf.extract(member, dest)
                    files.append(os.path.join(dest, member.name))
                except Exception:
                    pass
    return files


def read_text_from_archive_file(file_path: str, max_chars: int = 50000) -> str:
    """Читает текст из файла внутри архива."""
    try:
        with open(file_path, encoding="utf-8", errors="ignore") as f:
            return f.read(max_chars)
    except Exception:
        return ""
