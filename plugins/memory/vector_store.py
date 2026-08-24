from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable
import logging

logger = logging.getLogger(__name__)

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:  # pragma: no cover - optional runtime dependencies
    chromadb = None  # type: ignore
    Settings = None  # type: ignore

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover - optional runtime dependencies
    SentenceTransformer = None  # type: ignore

try:
    import numpy as np
except ImportError:  # pragma: no cover - optional runtime dependencies
    np = None  # type: ignore


_CLIENT = None
_COLLECTION = None
_EMBEDDER = None
_DEVICE: str | None = None


def _persist_dir() -> Path:
    return Path(__file__).resolve().parent / "database" / "chroma"


def init_vector_store(collection_name: str = "nexus_memory") -> None:
    global _CLIENT, _COLLECTION, _EMBEDDER
    if chromadb is None or SentenceTransformer is None:
        raise ImportError("chromadb and sentence-transformers are required for vector search")

    if _CLIENT is not None and _COLLECTION is not None and _EMBEDDER is not None:
        return

    persist = _persist_dir()
    persist.mkdir(parents=True, exist_ok=True)

    try:
        # Use the supported persistent client API in current Chroma versions.
        _CLIENT = chromadb.PersistentClient(path=str(persist))
    except Exception:
        # Fallback to an ephemeral client if persistence cannot be initialized.
        _CLIENT = chromadb.EphemeralClient()

    try:
        _COLLECTION = _CLIENT.get_collection(name=collection_name)
    except Exception:
        _COLLECTION = _CLIENT.create_collection(name=collection_name)

    # sentence-transformers model loaded once with device auto-selection
    # detect CUDA if available
    device_str = "cpu"
    try:
        import torch

        if torch.cuda.is_available():
            device_str = "cuda"
    except Exception:
        # torch may not be installed; default to cpu
        device_str = "cpu"

    # store device globally
    global _DEVICE
    _DEVICE = device_str

    _EMBEDDER = SentenceTransformer("all-MiniLM-L6-v2", device=device_str)


def _ensure_ready() -> None:
    global _EMBEDDER
    if chromadb is None or SentenceTransformer is None:
        raise ImportError("chromadb and sentence-transformers are required for vector search")
    if _CLIENT is None:
        init_vector_store()
    # ensure embedder is loaded even if client existed
    if _EMBEDDER is None:
        # initialize embedder with detected device
        try:
            device_str = _DEVICE or "cpu"
            _EMBEDDER = SentenceTransformer("all-MiniLM-L6-v2", device=device_str)
        except Exception:
            raise
  

def embed_texts(texts: Iterable[str]) -> list[list[float]]:
    _ensure_ready()
    # sentence-transformers returns numpy arrays when numpy is available
    if np is not None:
        arr = _EMBEDDER.encode(list(texts), convert_to_numpy=True)
    else:
        arr = _EMBEDDER.encode(list(texts), convert_to_numpy=False)
    return [list(map(float, a)) for a in arr]


def upsert_memory(memory_id: str, document: str, metadata: dict[str, Any]) -> None:
    """Create or update a vector document for the given memory_id."""
    _ensure_ready()
    vectors = embed_texts([document])
    # chroma upsert
    _COLLECTION.upsert(ids=[memory_id], documents=[document], metadatas=[metadata], embeddings=vectors)


def mark_deleted(memory_id: str, deleted: bool = True) -> None:
    """Mark a memory as deleted (updates metadata)."""
    _ensure_ready()
    # update metadata only
    # Chroma has 'update' with ids and metadatas
    _COLLECTION.update(ids=[memory_id], metadatas=[{"deleted": deleted}])


def query_vector(query: str, limit: int = 10, include_deleted: bool = False) -> list[dict[str, Any]]:
    """Query the vector store and return matching metadatas and ids."""
    _ensure_ready()
    vec = embed_texts([query])[0]
    try:
        results = _COLLECTION.query(
            query_embeddings=[vec],
            n_results=limit,
            include=["metadatas", "documents"],
        )  # type: ignore[arg-type]
    except Exception as exc:
        if "ids in query" in str(exc) or "Expected include item" in str(exc):
            logger.warning("Chroma query rejected include list; retrying without explicit include items")
            results = _COLLECTION.query(query_embeddings=[vec], n_results=limit)  # type: ignore[arg-type]
        else:
            raise

    metadatas = results.get("metadatas", [[]])[0]
    documents = results.get("documents", [[]])[0]
    ids = results.get("ids")
    if ids is None:
        ids = [
            [meta.get("memory_id") if isinstance(meta, dict) else None for meta in metadatas]
        ]
    ids = ids[0]

    out: list[dict[str, Any]] = []
    for mid, meta, doc in zip(ids, metadatas, documents):
        if not include_deleted and isinstance(meta, dict) and meta.get("deleted", False):
            continue

        entry = {"memory_id": mid}
        if isinstance(meta, dict):
            entry.update(meta)
        entry["document"] = doc
        out.append(entry)
    return out


def reset_store() -> None:
    """Delete persisted chroma directory (used by tests)."""
    global _CLIENT, _COLLECTION, _EMBEDDER

    try:
        if _CLIENT is not None and hasattr(_CLIENT, "close"):
            _CLIENT.close()
    except Exception:
        pass

    persist = _persist_dir()
    if persist.exists():
        import shutil

        try:
            shutil.rmtree(persist)
        except PermissionError:
            # Windows can keep a file handle open on the persistent Chroma data
            # directory until the client is closed. Retry once after closing the
            # client above, and fall back to a best-effort delete if needed.
            for attempt in range(3):
                try:
                    shutil.rmtree(persist)
                    break
                except PermissionError:
                    import time
                    time.sleep(0.1)

    _CLIENT = None
    _COLLECTION = None
    _EMBEDDER = None
