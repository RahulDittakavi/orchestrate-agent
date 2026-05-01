"""
retriever.py — Retrieves relevant support docs from ChromaDB for a given query.
"""

import os
import chromadb
from chromadb.utils import embedding_functions

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "chroma_db")
EMBED_MODEL = "all-MiniLM-L6-v2"

class Retriever:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=CHROMA_DIR)
        embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBED_MODEL
        )
        try:
            self.collection = self.client.get_collection(
                name="support_corpus",
                embedding_function=embed_fn
            )
            print("[✓] Retriever initialized")
        except Exception:
            self.collection = None
            print("[!] ChromaDB collection 'support_corpus' not found — run corpus_builder.py first. RAG disabled.")

    def retrieve(self, query: str, company: str = None, top_k: int = 5) -> list[dict]:
        """
        Retrieve top-k relevant docs for the query.
        If company is provided, filter by that source first,
        then fall back to all sources if not enough results.
        """
        # Map company name to source name
        source_map = {
            "HackerRank": "hackerrank",
            "Claude": "claude",
            "Visa": "visa"
        }

        if self.collection is None:
            return []

        where_filter = None
        if company and company in source_map:
            where_filter = {"source": source_map[company]}

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where_filter
            )
        except Exception:
            # Fallback: search all sources if filtered query fails
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k
            )

        docs = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 1.0
                docs.append({
                    "content": doc,
                    "source": meta.get("source", "unknown"),
                    "url": meta.get("url", ""),
                    "relevance_score": round(1 - distance, 3)  # Convert distance to similarity
                })

        return docs

    def format_docs_for_prompt(self, docs: list[dict]) -> str:
        """Format retrieved docs into a string for the LLM prompt."""
        if not docs:
            return "No relevant documentation found."

        formatted = []
        for i, doc in enumerate(docs, 1):
            formatted.append(
                f"[Doc {i}] Source: {doc['source'].upper()} | "
                f"Relevance: {doc['relevance_score']} | URL: {doc['url']}\n"
                f"{doc['content']}\n"
            )
        return "\n---\n".join(formatted)
