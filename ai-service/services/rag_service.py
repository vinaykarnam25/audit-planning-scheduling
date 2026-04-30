from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import chromadb
from sentence_transformers import SentenceTransformer

from services.config import settings
from services.text_utils import cosine_similarity


@dataclass(frozen=True)
class RagChunk:
    chunk_id: str
    source: str
    text: str


class RagService:
    _model = None

    def __init__(self) -> None:
        settings.chroma_path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(settings.chroma_path))
        self._collection = self._client.get_or_create_collection(
            name=settings.rag_collection_name
        )
        self._seed_marker = settings.chroma_path / "seed_manifest.json"

    def seed_from_directory(self, directory: Path | None = None) -> dict:
        data_dir = directory or settings.data_path / "domain_docs"
        documents = sorted(data_dir.glob("*.txt"))
        chunks: list[RagChunk] = []
        for document_path in documents:
            raw_text = document_path.read_text(encoding="utf-8").strip()
            for index, chunk in enumerate(self._chunk_text(raw_text)):
                chunk_id = self._chunk_id(document_path.name, index, chunk)
                chunks.append(
                    RagChunk(
                        chunk_id=chunk_id,
                        source=document_path.name,
                        text=chunk,
                    )
                )

        if chunks:
            self._collection.upsert(
                ids=[chunk.chunk_id for chunk in chunks],
                documents=[chunk.text for chunk in chunks],
                embeddings=self._embed_texts([chunk.text for chunk in chunks]),
                metadatas=[{"source": chunk.source} for chunk in chunks],
            )
            self._seed_marker.write_text(
                json.dumps(
                    {
                        "documents": len(documents),
                        "chunks": len(chunks),
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

        return {"documents": len(documents), "chunks": len(chunks)}

    def retrieve(self, query: str, limit: int = 3) -> list[dict]:
        if self._collection.count() == 0:
            self.seed_from_directory()

        try:
            results = self._collection.query(
                query_embeddings=[self._embed_texts([query])[0]],
                n_results=limit,
                include=["documents", "metadatas", "distances"],
            )
            documents = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            distances = results.get("distances", [[]])[0]
            scored = []
            for document, metadata, distance in zip(
                documents,
                metadatas,
                distances,
                strict=False,
            ):
                scored.append(
                    {
                        "content": document,
                        "source": (metadata or {}).get("source", "unknown"),
                        "score": round(max(0.0, 1 - float(distance)), 4),
                    }
                )
            return scored
        except Exception:
            return self._retrieve_lexically(query, limit)

    def build_context(self, query: str, limit: int = 3) -> list[dict]:
        return self.retrieve(query, limit=limit)

    def has_documents(self) -> bool:
        return self._collection.count() > 0 or self._seed_marker.exists()

    @classmethod
    def _embed_texts(cls, texts: list[str]) -> list[list[float]]:
        try:
            if cls._model is None:
                cls._model = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
            embeddings = cls._model.encode(texts)
            return [embedding.tolist() for embedding in embeddings]
        except Exception:
            return [cls._hashed_embedding(text) for text in texts]

    @staticmethod
    def _hashed_embedding(text: str, size: int = 32) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values = []
        for index in range(size):
            byte_value = digest[index % len(digest)]
            values.append(byte_value / 255.0)
        magnitude = math.sqrt(sum(value * value for value in values)) or 1.0
        return [value / magnitude for value in values]

    def _retrieve_lexically(self, query: str, limit: int) -> list[dict]:
        try:
            results = self._collection.get(include=["documents", "metadatas"])
            rows = zip(
                results.get("documents", []),
                results.get("metadatas", []),
                strict=False,
            )
        except Exception:
            rows = []

        scored = []
        for document, metadata in rows:
            score = cosine_similarity(query, document)
            scored.append(
                {
                    "content": document,
                    "source": (metadata or {}).get("source", "unknown"),
                    "score": round(score, 4),
                }
            )

        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:limit]

    @staticmethod
    def _chunk_text(text: str, size: int = 500, overlap: int = 50) -> Iterable[str]:
        if len(text) <= size:
            yield text
            return

        start = 0
        while start < len(text):
            end = start + size
            yield text[start:end]
            if end >= len(text):
                break
            start = end - overlap

    @staticmethod
    def _chunk_id(source: str, index: int, text: str) -> str:
        digest = hashlib.sha256(f"{source}:{index}:{text}".encode("utf-8")).hexdigest()
        return digest[:24]
