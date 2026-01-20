#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path

SKILL_ROOT = Path(__file__).parent.parent
MAIN_SCRIPT = SKILL_ROOT / "scripts" / "main_operation.py"

def verify():
    test_comment = "TEST_SCHEDULER_VERIFY"

    try:
        # Cleanup
        subprocess.run([sys.executable, str(MAIN_SCRIPT), "--action", "remove", "--comment", test_comment], capture_output=True)

        # 1. Add
        res = subprocess.run([sys.executable, str(MAIN_SCRIPT), "--action", "add",
                              "--cmd", "echo test", "--schedule", "* * * * *", "--comment", test_comment],
                              capture_output=True, text=True)
        if res.returncode != 0:
            print(f"✗ Add failed: {res.stderr}")
            return sys.exit(1)

        # 2. List
        res_list = subprocess.run([sys.executable, str(MAIN_SCRIPT), "--action", "list"], capture_output=True, text=True)
        if test_comment not in res_list.stdout:
            print("✗ Verify failed: Test schedule not found in list")
            return sys.exit(1)

        # 3. Remove
        res_rem = subprocess.run([sys.executable, str(MAIN_SCRIPT), "--action", "remove", "--comment", test_comment], capture_output=True, text=True)
        if res_rem.returncode != 0:
             print(f"✗ Remove failed: {res_rem.stderr}")
             return sys.exit(1)

        # 4. Check removal
        res_list2 = subprocess.run([sys.executable, str(MAIN_SCRIPT), "--action", "list"], capture_output=True, text=True)
        if test_comment in res_list2.stdout:
            print("✗ Verify failed: Test schedule still present after remove")
            return sys.exit(1)

        print("✓ Verification passed - Add, List, Remove workflow successful")
        sys.exit(0)

    except Exception as e:
        print(f"✗ Verification error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    verify()
