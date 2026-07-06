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

import zipfile
import xml.etree.ElementTree as ET

def extract_text_from_docx(docx_path: str) -> str:
    """Extracts text from a DOCX file by reading its main document XML."""
    try:
        paragraphs = []
        with zipfile.ZipFile(docx_path) as docx:
            xml_content = docx.read('word/document.xml')
            root = ET.fromstring(xml_content)
            namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            
            # Find all paragraph elements <w:p>
            for p in root.findall('.//w:p', namespaces):
                # For each paragraph, find all text elements <w:t>
                p_text = []
                for t in p.findall('.//w:t', namespaces):
                    if t.text:
                        p_text.append(t.text)
                if p_text:
                    paragraphs.append("".join(p_text))
            
            return "\n".join(paragraphs)
    except Exception as e:
        logger.error(f"Failed to extract text from docx: {str(e)}")
        return ""

def index_document(file_path: str) -> bool:
    """
    Parses pages from the target PDF or DOCX contract, chunks them, generates embeddings,
    and appends them to a local FAISS vector index.
    """
    if not os.path.exists(file_path):
        logger.error(f"Target file does not exist: {file_path}")
        return False

    filename = os.path.basename(file_path)
    chunks_extracted = []
    metadata_list = []

    if file_path.lower().endswith(".pdf"):
        try:
            reader = PdfReader(file_path)
            logger.info(f"Extracting text from PDF: {filename} ({len(reader.pages)} pages)")
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
        except Exception as e:
            logger.error(f"Failed to read PDF file: {str(e)}")
            return False

    elif file_path.lower().endswith(".docx"):
        try:
            logger.info(f"Extracting text from DOCX: {filename}")
            full_text = extract_text_from_docx(file_path)
            if not full_text or not full_text.strip():
                logger.warning(f"Empty text in DOCX document: {filename}")
                return False
            
            doc_chunks = chunk_document_text(full_text)
            for chunk_idx, chunk in enumerate(doc_chunks):
                chunks_extracted.append(chunk)
                metadata_list.append({
                    "source": filename,
                    "page": (chunk_idx // 4) + 1,  # Estimate ~4 chunks per page
                    "text": chunk
                })
        except Exception as e:
            logger.error(f"Failed to read DOCX file: {str(e)}")
            return False
    else:
        logger.error(f"Unsupported file type: {filename}")
        return False

    if not chunks_extracted:
        logger.warning(f"No text extracted from document: {filename}")
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
