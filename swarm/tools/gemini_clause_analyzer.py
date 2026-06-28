"""
swarm/tools/gemini_clause_analyzer.py
Uses Gemini model to extract and audit legal contract clauses from RAG document chunks.
"""

import json
import logging
import re
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types

logger = logging.getLogger("swarm.tools.gemini_clause_analyzer")

def analyze_clauses_with_gemini(
    target_company: str, 
    chunks: List[Dict[str, Any]], 
    api_key: str
) -> Optional[Dict[str, Any]]:
    """
    Passes RAG chunks to Gemini to identify legal risk categories corresponding to LQ-01 to LQ-10.
    Returns parsed findings dict, or None if API key is invalid/call fails.
    """
    if not api_key or api_key == "your_gemini_api_key_here" or not api_key.strip():
        logger.warning("No valid Gemini API key provided. Skipping AI contract clause analysis.")
        return None

    if not chunks:
        return {
            "flags": [],
            "hitl_required": False,
            "hitl_reasons": [],
            "red_flag_alerts": []
        }

    try:
        client = genai.Client(api_key=api_key)
        
        # Prepare context by formatting the document chunks
        formatted_chunks = []
        for i, chunk in enumerate(chunks):
            formatted_chunks.append(
                f"--- Chunk {i+1} ---\n"
                f"Source Document: {chunk.get('source', 'Unknown')}\n"
                f"Page Number: {chunk.get('page', 'Unknown')}\n"
                f"Text:\n{chunk.get('text', '')}\n"
            )
        
        chunks_context = "\n".join(formatted_chunks)
        
        system_instruction = (
            "You are the lead M&A Corporate Counsel Agent.\n"
            "Your task is to analyze legal contract chunks for risks regarding a target company acquisition.\n"
            "Audit the text specifically for these 10 categories:\n"
            "LQ-01: Poison Pill / Deal Blocker (Change-of-control clauses, successor requirements)\n"
            "LQ-02: Active Litigation (Pending or threatened lawsuits, arbitration)\n"
            "LQ-03: IP Risk (IP disputes, contested ownership, copyleft/GPL licenses)\n"
            "LQ-04: Indemnification / Financial Exposure (Caps, limits, hold harmless clauses)\n"
            "LQ-05: HR Liability / Golden Parachute (Severance, golden parachutes, retention payouts)\n"
            "LQ-06: Operational Lock-in / Non-compete (Non-compete, exclusivity, non-solicitation)\n"
            "LQ-07: Regulatory Risk / Data Privacy (GDPR, CCPA, data breaches, regulatory reviews)\n"
            "LQ-08: Financial Exposure / Revenue Guarantees (Minimum purchases, earn-outs, MFN clauses)\n"
            "LQ-09: Deal Blocker / Third-Party Consent (Prior written approvals, lender consents)\n"
            "LQ-10: Operational Lock-in / Auto-renewal (Evergreen clauses, lock-in terms, termination fees)\n\n"
            "Classification Rules:\n"
            "- Severity 1 (🔴 CRITICAL): Liability > $1M OR deal-blocking consent missing OR active lawsuit.\n"
            "- Severity 2 (🟠 HIGH): Liability $100K-$1M OR material operational restriction post-acquisition.\n"
            "- Severity 3 (🟡 MEDIUM): Liability < $100K OR standard clauses with non-trivial terms.\n"
            "- Severity 4 (🟢 LOW): Boilerplate clauses, no material risk (do not report LOW findings).\n\n"
            "You MUST output your response strictly as a JSON object matching this schema:\n"
            "{\n"
            "  \"flags\": [\n"
            "    {\n"
            "      \"lq_id\": \"LQ-01\" to \"LQ-10\",\n"
            "      \"severity\": 1 or 2 or 3,\n"
            "      \"severity_label\": \"🔴 CRITICAL\" or \"🟠 HIGH\" or \"🟡 MEDIUM\",\n"
            "      \"category\": \"<matching Category Name from the list above>\",\n"
            "      \"document\": \"<exact source filename from the chunk>\",\n"
            "      \"page\": <page number as integer from the chunk>,\n"
            "      \"quote\": \"<verbatim quote showing the clause, max 150 words>\",\n"
            "      \"matched_keywords\": [\"keyword1\", \"keyword2\"],\n"
            "      \"description\": \"<plain-English description of the finding and the risk it presents>\",\n"
            "      \"estimated_exposure\": \"<estimated dollar liability, e.g., $1.5M, or 'Unquantified'>\",\n"
            "      \"recommended_action\": \"<actionable advice, e.g. Seek consent, Renegotiate, Adjust valuation>\"\n"
            "    }\n"
            "  ]\n"
            "}\n\n"
            "Rules:\n"
            "- Only raise flags if they are genuinely present in the text.\n"
            "- Make sure you output verbatim quotes only.\n"
            "- Ensure the JSON is completely valid."
        )

        user_prompt = (
            f"Target Company to evaluate: {target_company}\n\n"
            f"Analyze the following contract document chunks and return the JSON findings report:\n\n"
            f"{chunks_context}"
        )

        # Call Gemini (using gemini-2.5-flash)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json"
            )
        )
        
        response_text = response.text.strip()
        
        # Clean up potential markdown formatting block if the model included it despite instructions
        if response_text.startswith("```"):
            response_text = re.sub(r"^```(?:json)?\n", "", response_text)
            response_text = re.sub(r"\n```$", "", response_text)
            response_text = response_text.strip()

        findings = json.loads(response_text)
        logger.info(f"Gemini clause analysis succeeded, generated {len(findings.get('flags', []))} flags.")
        return findings

    except Exception as e:
        logger.error(f"Gemini clause analysis failed: {str(e)}. Falling back to keyword search.", exc_info=True)
        return None
