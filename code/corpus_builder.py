"""
corpus_builder.py — Reads scraped .txt files and embeds them into ChromaDB.
Run this ONCE after scraper.py:  python corpus_builder.py

Creates a persistent vector DB in data/chroma_db/
"""

import os
import chromadb
from chromadb.utils import embedding_functions
from rich.progress import track

CORPUS_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "corpus")
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "chroma_db")

# Using sentence-transformers for local embeddings (no API cost)
EMBED_MODEL = "all-MiniLM-L6-v2"

def chunk_text(text, chunk_size=500, overlap=50):
    """Split long docs into overlapping chunks for better retrieval."""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks

def build_corpus():
    print("=" * 50)
    print("Building ChromaDB Corpus")
    print("=" * 50)

    # Init ChromaDB
    client = chromadb.PersistentClient(path=CHROMA_DIR)

    # Delete existing collection if rebuilding
    try:
        client.delete_collection("support_corpus")
        print("[!] Deleted existing collection, rebuilding...")
    except:
        pass

    # Use sentence-transformers embedding (runs locally, free)
    embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBED_MODEL
    )

    collection = client.create_collection(
        name="support_corpus",
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"}
    )

    all_chunks = []
    all_ids = []
    all_metadata = []

    sources = ["hackerrank", "claude", "visa"]

    for source in sources:
        source_dir = os.path.join(CORPUS_DIR, source)
        if not os.path.exists(source_dir):
            print(f"[!] No corpus found for {source} — run scraper.py first")
            continue

        files = [f for f in os.listdir(source_dir) if f.endswith(".txt")]
        print(f"\n[→] Processing {source}: {len(files)} files")

        for filename in track(files, description=f"  Embedding {source}..."):
            filepath = os.path.join(source_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract URL from first lines
            url = ""
            for line in content.split("\n")[:3]:
                if line.startswith("URL:"):
                    url = line.replace("URL:", "").strip()

            chunks = chunk_text(content)
            for j, chunk in enumerate(chunks):
                chunk_id = f"{source}_{filename}_{j}"
                all_chunks.append(chunk)
                all_ids.append(chunk_id)
                all_metadata.append({
                    "source": source,
                    "file": filename,
                    "url": url,
                    "chunk_index": j
                })

    # Batch insert into ChromaDB
    print(f"\n[→] Inserting {len(all_chunks)} chunks into ChromaDB...")
    batch_size = 100
    for i in range(0, len(all_chunks), batch_size):
        collection.add(
            documents=all_chunks[i:i + batch_size],
            ids=all_ids[i:i + batch_size],
            metadatas=all_metadata[i:i + batch_size]
        )

    print(f"\n[✓] Corpus built. Total chunks: {len(all_chunks)}")
    print(f"[✓] ChromaDB saved to: {CHROMA_DIR}")

if __name__ == "__main__":
    build_corpus()
