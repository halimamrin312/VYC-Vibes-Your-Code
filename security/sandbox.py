"""
security/sandbox.py
Implements EphemeralSandbox for executing untrusted scripts inside isolated python subprocesses.
"""

import subprocess
import tempfile
import os
import sys
from pathlib import Path
from security.policy_engine import ToolPolicyEngine

class EphemeralSandbox:
    """Simulates isolated script execution wrapper for the Financial Auditor."""
    def __init__(self, policy_engine: ToolPolicyEngine):
        self.policy_engine = policy_engine

    def execute_script(self, script_content: str, data_path: str) -> str:
        # Enforce policy checks before spinning up subprocess
        self.policy_engine.validate_code_structure(script_content)
        self.policy_engine.validate_file_path(data_path)

        # Resolve scratch directory path dynamically for portability (env var or project local path)
        scratch_dir = os.environ.get("SANDBOX_SCRATCH_DIR")
        if not scratch_dir:
            scratch_dir = os.path.abspath(os.path.join(os.getcwd(), "scratch"))
        os.makedirs(scratch_dir, exist_ok=True)

        with tempfile.TemporaryDirectory(dir=scratch_dir) as temp_dir:
            temp_script = Path(temp_dir) / "sandbox_audit.py"
            temp_script.write_text(script_content, encoding="utf-8")

            # Execute code inside downscoped subprocess, capping run time at 10s
            try:
                result = subprocess.run(
                    [sys.executable, str(temp_script), data_path],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=True
                )
                return result.stdout
            except subprocess.TimeoutExpired:
                raise TimeoutError("Execution halted: Sandbox resource limit exceeded.")
            except subprocess.CalledProcessError as e:
                return f"Execution Error: {e.stderr}"
