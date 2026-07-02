"""
swarm/tools/local_pdf_parser.py
Extracts PDF text, performs chunking, generates embeddings using sentence-transformers,
and executes local similarity searches via FAISS. Zero data leaks to external index systems.
"""

import os
import pickle
import logging
from typing import List, Dict, Any
import numpy as np
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import faiss

# Configure logger
logger = logging.getLogger("swarm.tools.local_pdf_parser")

MODEL_NAME = 'all-MiniLM-L6-v2'
INDEX_PATH = "data_room/vector_store/faiss_index.index"
METADATA_PATH = "data_room/vector_store/metadata.pkl"

def get_transformer_model() -> SentenceTransformer:
    """Helper to initialize the SentenceTransformer model locally."""
    return SentenceTransformer(MODEL_NAME)

def chunk_document_text(text: str, chunk_size_words: int = 250, overlap_words: int = 30) -> List[str]:
    """Helper function to split text into overlapping word chunks."""
    words = text.split()
    if len(words) <= chunk_size_words:
        return [" ".join(words)]
        
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size_words])
        chunks.append(chunk)
        i += (chunk_size_words - overlap_words)
    return chunks

# Alias for compatibility with test imports
chunk_text = chunk_document_text

def index_document(pdf_path: str) -> bool:
    """
    Parses pages from the target PDF contract, chunks them, generates embeddings,
    and appends them to a local FAISS vector index.
    """
    if not os.path.exists(pdf_path):
        logger.error(f"Target PDF file does not exist: {pdf_path}")
        return False

    try:
        reader = PdfReader(pdf_path)
    except Exception as e:
        logger.error(f"Failed to read PDF file: {str(e)}")
        return False
        
    filename = os.path.basename(pdf_path)
    logger.info(f"Extracting text from: {filename} ({len(reader.pages)} pages)")

    chunks_extracted = []
    metadata_list = []

    for page_idx, page in enumerate(reader.pages):
        text = page.extract_text()
        if not text or not text.strip():
            logger.warning(f"Empty text on page {page_idx + 1} of {filename}")
            continue
            
        page_chunks = chunk_document_text(text)
        for chunk in page_chunks:
            chunks_extracted.append(chunk)
            metadata_list.append({
                "source": filename,
                "page": page_idx + 1,
                "text": chunk
            })

    if not chunks_extracted:
        logger.warning(f"No text extracted from PDF document: {filename}")
        return False

    # Generate Embeddings
    model = get_transformer_model()
    embeddings = model.encode(chunks_extracted)
    
    # Store in FAISS
    os.makedirs("data_room/vector_store", exist_ok=True)
    dimension = embeddings.shape[1]
    
    if os.path.exists(INDEX_PATH) and os.path.exists(METADATA_PATH):
        try:
            index = faiss.read_index(INDEX_PATH)
            with open(METADATA_PATH, 'rb') as f:
                existing_metadata = pickle.load(f)
        except Exception as e:
            logger.error(f"Failed to read existing FAISS index. Initializing new database. Error: {str(e)}")
            index = faiss.IndexFlatL2(dimension)
            existing_metadata = []
    else:
        index = faiss.IndexFlatL2(dimension)
        existing_metadata = []

    # Add embeddings to the FLAT index
    index.add(np.array(embeddings).astype('float32'))
    existing_metadata.extend(metadata_list)

    # Save to disk
    try:
        faiss.write_index(index, INDEX_PATH)
        with open(METADATA_PATH, 'wb') as f:
            pickle.dump(existing_metadata, f)
        logger.info(f"Successfully indexed {len(chunks_extracted)} chunks from {filename}")
        return True
    except Exception as e:
        logger.error(f"Failed to write FAISS index files to disk: {str(e)}")
        return False

def query_local_vector_store(query_text: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Executes a vector search over the local database.
    Returns matching document chunks with corresponding source metadata.
    """
    if not os.path.exists(INDEX_PATH) or not os.path.exists(METADATA_PATH):
        logger.warning("Query execution failed: No local vector store index found.")
        return []

    try:
        model = get_transformer_model()
        query_emb = model.encode([query_text]).astype('float32')

        index = faiss.read_index(INDEX_PATH)
        with open(METADATA_PATH, 'rb') as f:
            metadata = pickle.load(f)

        distances, indices = index.search(query_emb, top_k)
        
        results = []
        for rank, index_idx in enumerate(indices[0]):
            if index_idx < len(metadata):
                results.append({
                    "rank": rank + 1,
                    "score": float(distances[0][rank]),
                    "page": metadata[index_idx]["page"],
                    "source": metadata[index_idx]["source"],
                    "text": metadata[index_idx]["text"]
                })
        return results
    except Exception as e:
        logger.error(f"Vector search failed: {str(e)}")
        return []
