#!/usr/bin/env python3
import sys
import subprocess
import os
from pathlib import Path

# Config
SKILL_ROOT = Path(__file__).parent.parent
MAIN_SCRIPT = SKILL_ROOT / "scripts" / "main_operation.py"
VAULT_ROOT = Path("AI_Employee_Vault")
PENDING_DIR = VAULT_ROOT / "Pending_Approval"
APPROVED_DIR = VAULT_ROOT / "Approved"

def verify():
    test_file = PENDING_DIR / "TEST_APPROVAL_VERIFY.md"

    try:
        # cleanup
        if (APPROVED_DIR / test_file.name).exists():
            (APPROVED_DIR / test_file.name).unlink()

        # 1. Create test file
        PENDING_DIR.mkdir(parents=True, exist_ok=True)
        test_file.write_text("---\ntype: test\n---\nTest Content")

        # 2. List (should contain file)
        res = subprocess.run([sys.executable, str(MAIN_SCRIPT), "--action", "list"], capture_output=True, text=True)
        if test_file.name not in res.stdout:
            print("✗ List failed: Test file not found in output")
            return sys.exit(1)

        # 3. Approve
        res = subprocess.run([sys.executable, str(MAIN_SCRIPT), "--action", "approve", "--id", test_file.name], capture_output=True, text=True)
        if res.returncode != 0:
             print(f"✗ Approve command failed: {res.stderr}")
             return sys.exit(1)

        # 4. Check move
        if not (APPROVED_DIR / test_file.name).exists():
            print("✗ Check failed: File not moved to Approved")
            return sys.exit(1)

        # Cleanup
        (APPROVED_DIR / test_file.name).unlink()

        print("✓ Verification passed - List and Approve workflows functioning")
        sys.exit(0)

    except Exception as e:
        print(f"✗ Verification error: {str(e)}")
        if test_file.exists(): test_file.unlink()
        sys.exit(1)

if __name__ == "__main__":
    verify()
