"""
backend/app/utils/sanitizer.py
Input validation and path traversal sanitization helpers for the M&A Swarm API.
"""

import os
import re

def sanitize_input_string(input_str: str) -> str:
    """
    Sanitizes raw string inputs to remove potential injection vectors or zero-width poison characters.
    """
    if not input_str:
        return ""
    # Strip zero-width unicode characters (homoglyphs)
    clean = re.sub(r"[\u200B-\u200D\uFEFF\u200E\u200F]", "", input_str)
    # Strip control characters except newline and tab
    clean = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]", "", clean)
    # Strip standard HTML tags
    clean = re.sub(r"<[^>]*>", "", clean)
    return clean.strip()

def sanitize_filename(filename: str) -> str:
    """
    Sanitizes file upload filenames to prevent directory traversal attacks.
    """
    if not filename:
        return "unnamed_file"
    # Extract only the base name
    base = os.path.basename(filename)
    # Allow only alphanumeric characters, dots, underscores, and hyphens
    clean = re.sub(r"[^\w\.\-]", "_", base)
    # Prevent traversal indicators
    clean = clean.replace("..", "_")
    return clean
