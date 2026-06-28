"""
chunk_and_embed.py — Fallback document ingestion script for Legal & Compliance Agent.

Use this when the MCP FileSystem pipeline is unavailable.
Chunks PDFs/DOCX into semantic segments and pushes embeddings to the vector store.

Usage:
    python scripts/chunk_and_embed.py --input_dir ./contracts --collection legal_docs

Requirements:
    pip install pypdf python-docx langchain-text-splitters chromadb sentence-transformers
"""

import argparse
import os
import json
from pathlib import Path

# ── PDF reader ────────────────────────────────────────────────────────────────
def read_pdf(path: str) -> str:
    from pypdf import PdfReader
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)

# ── DOCX reader ───────────────────────────────────────────────────────────────
def read_docx(path: str) -> str:
    from docx import Document
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)

# ── Plain text reader ─────────────────────────────────────────────────────────
def read_txt(path: str) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")

# ── Dispatch by extension ──────────────────────────────────────────────────────
READERS = {
    ".pdf": read_pdf,
    ".docx": read_docx,
    ".txt": read_txt,
    ".md": read_txt,
}

def read_document(path: str) -> str:
    ext = Path(path).suffix.lower()
    reader = READERS.get(ext)
    if not reader:
        raise ValueError(f"Unsupported file type: {ext}")
    return reader(path)

# ── Chunking ──────────────────────────────────────────────────────────────────
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Simple character-based chunking with overlap."""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks

# ── Embedding + Vector Store ──────────────────────────────────────────────────
def embed_and_store(chunks: list[str], doc_name: str, collection_name: str):
    import chromadb
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("all-MiniLM-L6-v2")
    client = chromadb.Client()
    collection = client.get_or_create_collection(collection_name)

    embeddings = model.encode(chunks).tolist()
    ids = [f"{doc_name}::chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"source": doc_name, "chunk_index": i} for i in range(len(chunks))]

    collection.add(
        documents=chunks,
        embeddings=embeddings,
        ids=ids,
        metadatas=metadatas,
    )
    return len(chunks)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Chunk and embed legal documents.")
    parser.add_argument("--input_dir", required=True, help="Directory containing documents")
    parser.add_argument("--collection", default="legal_docs", help="Vector store collection name")
    parser.add_argument("--chunk_size", type=int, default=500, help="Words per chunk")
    parser.add_argument("--overlap", type=int, default=50, help="Word overlap between chunks")
    args = parser.parse_args()

    input_path = Path(args.input_dir)
    supported = list(READERS.keys())
    files = [f for f in input_path.iterdir() if f.suffix.lower() in supported]

    if not files:
        print(f"[WARNING] No supported documents found in {args.input_dir}")
        print(f"  Supported types: {supported}")
        return

    total_chunks = 0
    skipped = []

    for f in files:
        try:
            print(f"[INFO] Reading {f.name} ...")
            text = read_document(str(f))
            if not text.strip():
                print(f"[WARNING] {f.name} appears empty or unreadable — skipping.")
                skipped.append(f.name)
                continue
            chunks = chunk_text(text, args.chunk_size, args.overlap)
            n = embed_and_store(chunks, f.name, args.collection)
            total_chunks += n
            print(f"  ✓ {f.name} — {n} chunks embedded.")
        except Exception as e:
            print(f"[ERROR] Failed to process {f.name}: {e}")
            skipped.append(f.name)

    print(f"\n[DONE] Total chunks embedded: {total_chunks}")
    print(f"       Collection: '{args.collection}'")
    if skipped:
        print(f"[SKIPPED — manual review required]: {skipped}")

    # Write a manifest for the Legal Agent to reference
    manifest = {
        "collection": args.collection,
        "total_chunks": total_chunks,
        "indexed_files": [f.name for f in files if f.name not in skipped],
        "unreviewed_files": skipped,
    }
    manifest_path = input_path / "ingestion_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"[MANIFEST] Written to {manifest_path}")

if __name__ == "__main__":
    main()
