"""
security/policy_engine.py
Implements the ContextResolver and ToolPolicyEngine to sanitize inputs and restrict agent tools.
"""

import re
import yaml
import ast
from pathlib import Path

class ContextResolver:
    """Sanitizes context buffers to prevent indirect prompt injection."""
    def __init__(self):
        # Match zero-width characters and invisible homoglyphs
        self.homoglyph_pattern = re.compile(r"[\u200B-\u200D\uFEFF\u200E\u200F]")

    def sanitize_context(self, raw_text: str) -> str:
        if not raw_text:
            return ""
        # Strip zero-width poison characters
        clean_text = self.homoglyph_pattern.sub("", raw_text)
        # Strip system env variables if accidentally leaked in context
        clean_text = re.sub(r"ENV_[A-Z0-9_]+", "[REDACTED_ENV]", clean_text)
        return clean_text

class ToolPolicyEngine:
    """Enforces structural and semantic rules on tools executed by agents."""
    def __init__(self, config_path: str):
        with open(config_path, "r", encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        self.rules = self.config["gating_rules"]

    def validate_code_structure(self, python_code: str) -> bool:
        # 1. Structural Gating: Check blocked commands
        for command in self.rules["blocked_commands"]:
            if command in python_code:
                raise PermissionError(f"Security Policy Block: Blocked command detected: {command}")

        # 2. Structural Gating: Verify imports are within allowlist using AST
        try:
            tree = ast.parse(python_code)
        except SyntaxError as e:
            raise ValueError(f"Security Policy Block: Invalid python syntax: {str(e)}")

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split('.')[0]
                    if module not in self.rules["allowed_modules"]:
                        raise PermissionError(f"Security Policy Block: Unauthorized module import: {module}")
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module.split('.')[0]
                    if module not in self.rules["allowed_modules"]:
                        raise PermissionError(f"Security Policy Block: Unauthorized module import: {module}")

        return True

    def validate_file_path(self, target_path: str) -> bool:
        normalized_path = str(Path(target_path).resolve())
        # Enforce file-tree directory allowlist
        for allowed_dir in self.rules["directory_allowlist"]:
            allowed_dir_norm = str(Path(allowed_dir).resolve())
            if normalized_path.startswith(allowed_dir_norm):
                return True
        raise PermissionError(f"Security Policy Block: Unauthorized path write: {target_path}")
