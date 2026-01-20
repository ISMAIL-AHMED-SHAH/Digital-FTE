#!/usr/bin/env python3
import sys
import subprocess
import os
from pathlib import Path

# Config
SKILL_ROOT = Path(__file__).parent.parent
MAIN_SCRIPT = SKILL_ROOT / "scripts" / "main_operation.py"

def verify():
    test_subj = "TEST_EMAIL_VERIFY"

    try:
        # 1. Send test email
        env = os.environ.copy()
        env["DRY_RUN"] = "true"

        args = [sys.executable, str(MAIN_SCRIPT), "--action", "send",
                "--to", "test@example.com",
                "--subject", test_subj,
                "--body", "This is a test email"]

        res = subprocess.run(args, capture_output=True, text=True, env=env)

        if res.returncode != 0:
            print(f"✗ Send command failed: {res.stderr}")
            return sys.exit(1)

        # 2. Check logs (via list-sent)
        res_list = subprocess.run([sys.executable, str(MAIN_SCRIPT), "--action", "list-sent", "--limit", "1"], capture_output=True, text=True, env=env)

        if test_subj not in res_list.stdout:
             print("✗ Verify failed: Test email not found in sent logs")
             return sys.exit(1)

        print("✓ Verification passed - Email Send and Log Check successful")
        sys.exit(0)

    except Exception as e:
        print(f"✗ Verification error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    verify()
