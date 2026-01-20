#!/usr/bin/env python3
import sys
import subprocess
import os
from pathlib import Path

SKILL_ROOT = Path(__file__).parent.parent
MAIN_SCRIPT = SKILL_ROOT / "scripts" / "main_operation.py"

def verify():
    test_content = "TEST_SOCIAL_POST_VERIFY"

    try:
        env = os.environ.copy()
        env["DRY_RUN"] = "true"

        # 1. Post content
        res = subprocess.run([sys.executable, str(MAIN_SCRIPT), "--action", "post", "--content", test_content], capture_output=True, text=True, env=env)
        if res.returncode != 0:
            print(f"✗ Post failed: {res.stderr}")
            return sys.exit(1)

        # 2. Check logs
        res_list = subprocess.run([sys.executable, str(MAIN_SCRIPT), "--action", "list-recent", "--limit", "1"], capture_output=True, text=True, env=env)
        if test_content not in res_list.stdout:
            print("✗ Verify failed: Test post not found in log")
            return sys.exit(1)

        # 3. Test duplicate detection
        res_dup = subprocess.run([sys.executable, str(MAIN_SCRIPT), "--action", "post", "--content", test_content], capture_output=True, text=True, env=env)
        if "Duplicate content detected" not in res_dup.stdout:
            print("✗ Verify failed: Duplicate not detected")
            return sys.exit(1)

        print("✓ Verification passed - Post, Log, and Duplicate Check successful")
        sys.exit(0)

    except Exception as e:
        print(f"✗ Verification error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    verify()
