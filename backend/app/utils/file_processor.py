"""
backend/app/utils/file_processor.py
Utility functions for processing ingested documents (CSV validation, PDF text extraction).
"""

import os
import pandas as pd
from pypdf import PdfReader
import logging

logger = logging.getLogger("backend.app.utils.file_processor")

def process_csv(file_path: str, required_columns: list = None) -> pd.DataFrame:
    """
    Reads a CSV file, performs schema validation, and returns a pandas DataFrame.
    Raises ValueError if required columns are missing.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    try:
        df = pd.read_csv(file_path)
        if required_columns:
            missing_cols = [col for col in required_columns if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")
        return df
    except Exception as e:
        logger.error(f"Error processing CSV {file_path}: {str(e)}")
        raise

def process_pdf(file_path: str) -> str:
    """
    Extracts text from a local PDF document page by page.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    try:
        reader = PdfReader(file_path)
        extracted_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                extracted_text.append(text)
        return "\n".join(extracted_text)
    except Exception as e:
        logger.error(f"Error extracting PDF text from {file_path}: {str(e)}")
        raise
