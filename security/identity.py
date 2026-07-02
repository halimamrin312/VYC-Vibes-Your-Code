"""
security/identity.py
Implements the VibeDiffGenerator for presenting human-readable security and financial diffs.
"""

class VibeDiffGenerator:
    """Translates agent code changes into human-reviewable summaries."""
    @staticmethod
    def generate_vibe_diff(original_intent: str, proposed_action: str) -> str:
        summary = (
            f"=== SECURITY VIBE DIFF REVIEW ===\n"
            f"Original Intent: {original_intent}\n"
            f"Proposed Action: {proposed_action}\n"
            f"---------------------------------\n"
            f"ALERT: This action carries high financial impact. Please plug in your "
            f"hardware FIDO2 key and approve this change."
        )
        return summary
