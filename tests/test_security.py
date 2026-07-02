"""
tests/test_security.py
Pytest suite verifying the security policy engines, ephemeral sandboxes, and context hygiene.
"""

import pytest
import os
import shutil
from security.policy_engine import ContextResolver, ToolPolicyEngine
from security.sandbox import EphemeralSandbox
from security.identity import VibeDiffGenerator

def test_context_resolver_zero_width_chars():
    resolver = ContextResolver()
    # zero-width spaces, joiners, BOM
    poisoned_text = "Acme\u200BCorp\u200D\uFEFFLtd"
    assert resolver.sanitize_context(poisoned_text) == "AcmeCorpLtd"

def test_context_resolver_env_redaction():
    resolver = ContextResolver()
    poisoned_text = "Leaked: ENV_DATABASE_PASSWORD and ENV_SECRET_KEY"
    assert resolver.sanitize_context(poisoned_text) == "Leaked: [REDACTED_ENV] and [REDACTED_ENV]"

def test_policy_engine_allowed_imports(tmp_path):
    config_yaml = tmp_path / "security_config.yaml"
    config_yaml.write_text("""
gating_rules:
  allowed_modules:
    - pandas
    - numpy
  blocked_commands:
    - os.system
  directory_allowlist:
    - "/tmp"
""")
    engine = ToolPolicyEngine(str(config_yaml))
    
    # Check permitted import structure
    assert engine.validate_code_structure("import pandas as pd\ndf = pd.DataFrame()") is True
    assert engine.validate_code_structure("from numpy import array\na = array([1, 2])") is True

def test_policy_engine_blocked_imports(tmp_path):
    config_yaml = tmp_path / "security_config.yaml"
    config_yaml.write_text("""
gating_rules:
  allowed_modules:
    - pandas
  blocked_commands:
    - os.system
  directory_allowlist:
    - "/tmp"
""")
    engine = ToolPolicyEngine(str(config_yaml))

    # Test unauthorized module import
    with pytest.raises(PermissionError, match="Unauthorized module import: sys"):
        engine.validate_code_structure("import sys\nsys.exit(1)")

def test_policy_engine_blocked_commands(tmp_path):
    config_yaml = tmp_path / "security_config.yaml"
    config_yaml.write_text("""
gating_rules:
  allowed_modules:
    - pandas
  blocked_commands:
    - os.system
    - subprocess.Popen
  directory_allowlist:
    - "/tmp"
""")
    engine = ToolPolicyEngine(str(config_yaml))

    # Test blocked command in code
    with pytest.raises(PermissionError, match="Blocked command detected: os.system"):
        engine.validate_code_structure("import pandas\nos.system('echo vulnerability')")

def test_policy_engine_directory_allowlist(tmp_path):
    # Setup allowed and disallowed paths
    allowed_dir = tmp_path / "scratch"
    allowed_dir.mkdir()
    disallowed_dir = tmp_path / "secrets"
    disallowed_dir.mkdir()

    allowed_dir_str = str(allowed_dir).replace('\\', '/')
    config_yaml = tmp_path / "security_config.yaml"
    config_yaml.write_text(f"""
gating_rules:
  allowed_modules:
    - pandas
  blocked_commands:
    - os.system
  directory_allowlist:
    - "{allowed_dir_str}"
""")
    engine = ToolPolicyEngine(str(config_yaml))

    allowed_file = allowed_dir / "target.csv"
    disallowed_file = disallowed_dir / "passwords.txt"

    assert engine.validate_file_path(str(allowed_file)) is True

    with pytest.raises(PermissionError, match="Unauthorized path write"):
        engine.validate_file_path(str(disallowed_file))

def test_ephemeral_sandbox_execution(tmp_path):
    allowed_dir = tmp_path / "scratch"
    allowed_dir.mkdir()
    
    # We must mock or create scratch workspace at the expected path
    # EphemeralSandbox writes temporary scripts to "d:/kaggle capstone project/scratch/"
    # Let's ensure the path exists
    os.makedirs("d:/kaggle capstone project/scratch/", exist_ok=True)

    allowed_dir_str = str(allowed_dir).replace('\\', '/')
    config_yaml = tmp_path / "security_config.yaml"
    config_yaml.write_text(f"""
gating_rules:
  allowed_modules:
    - pandas
    - sys
  blocked_commands:
    - os.system
  directory_allowlist:
    - "{allowed_dir_str}"
    - "d:/kaggle capstone project/scratch/"
""")
    engine = ToolPolicyEngine(str(config_yaml))
    sandbox = EphemeralSandbox(engine)

    # Safe script execution
    safe_script = """
import pandas as pd
import sys
# Subprocess runs python <script> <data_path>
data_path = sys.argv[1]
print(f"Reading file from {data_path}")
"""
    result = sandbox.execute_script(safe_script, str(allowed_dir / "data.csv"))
    assert "Reading file from" in result

def test_vibe_diff_generator():
    diff = VibeDiffGenerator.generate_vibe_diff(
        "Run standard audit",
        "Delete all operational backups"
    )
    assert "Original Intent: Run standard audit" in diff
    assert "Proposed Action: Delete all operational backups" in diff
    assert "hardware FIDO2 key" in diff
