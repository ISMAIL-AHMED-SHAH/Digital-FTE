#!/usr/bin/env python3
"""
Script to initialize a new Claude Code skill with MCP Code Execution patterns for efficiency.
"""

import os
import sys
from pathlib import Path


def create_skill(skill_name, output_dir="."):
    """
    Create a new Claude Code skill with efficient MCP Code Execution structure.

    Args:
        skill_name (str): Name of the skill (will be converted to lowercase with hyphens)
        output_dir (str): Directory where the skill should be created
    """
    # Sanitize skill name (lowercase, replace spaces with hyphens)
    sanitized_name = skill_name.lower().replace(' ', '-').replace('_', '-')

    # Validate skill name length
    if len(sanitized_name) > 64:
        raise ValueError(f"Skill name too long: {len(sanitized_name)} characters. Maximum is 64.")

    # Create skill directory
    skill_dir = Path(output_dir) / sanitized_name
    skill_dir.mkdir(exist_ok=True)

    # Create subdirectories
    (skill_dir / "scripts").mkdir(exist_ok=True)

    # Create default SKILL.md with MCP Code Execution pattern
    skill_content = f'''---
name: {sanitized_name}
description: "WHAT: [Clear statement of what this skill does and what problem it solves]. WHEN: User says '[common phrases]', '[task descriptions]', mentions [related technologies/concepts]. Trigger on: [keywords, patterns, task types]."
---

# {skill_name.replace('-', ' ').title()}

## When to Use
- [Specific scenario 1 where this skill is needed]
- [Specific scenario 2 where this skill is needed]
- [Specific scenario 3 where this skill is needed]

## Instructions
1. Execute primary operation: `python scripts/main_operation.py [args]`
2. Verify results: `python scripts/verify_operation.py`
3. Confirm success before proceeding with dependent tasks.

## Validation
- [ ] Primary operation completed successfully
- [ ] Results verified and confirmed
- [ ] No sensitive data exposed in output

See [REFERENCE.md](./REFERENCE.md) for detailed configuration options.
'''

    # Create default REFERENCE.md
    reference_content = f"""# {skill_name.replace('-', ' ').title()} Reference

Detailed documentation for the {skill_name} skill. This file is loaded only when the agent needs deep configuration details.

## Configuration Options

### Environment Variables
- `EXAMPLE_VAR`: Description of what this variable controls
- `ANOTHER_VAR`: Description of another configuration option

### Script Parameters
- **main_operation.py**: Accepts arguments for [describe main operation]
- **verify_operation.py**: Validates [describe validation logic]

## Advanced Usage

### Scenario 1: Advanced Configuration
[Detailed explanation of advanced usage patterns]

### Scenario 2: Integration with Other Systems
[How this skill integrates with related systems or skills]

### Scenario 3: Error Handling
[Common errors and how scripts handle them]

## Troubleshooting

### Issue: [Common Problem]
**Symptoms**: [What you'll see]
**Solution**: [How to resolve]

### Issue: [Another Problem]
**Symptoms**: [What you'll see]
**Solution**: [How to resolve]

## Examples

### Example 1: Basic Usage
```bash
python scripts/main_operation.py --option value
python scripts/verify_operation.py
```

### Example 2: Advanced Usage
```bash
# Multi-step operation
python scripts/main_operation.py --advanced-flag
python scripts/verify_operation.py --strict
```
"""

    # Create a sample main script demonstrating MCP Code Execution pattern
    main_script_content = '''#!/usr/bin/env python3
"""
Main operation script - performs heavy lifting outside the context window.
Returns minimal, meaningful output to the agent.

Usage:
    python main_operation.py [args]
"""
import subprocess
import json
import sys
import os

def main():
    """
    Execute the main operation.
    
    This script should:
    1. Interact with external systems (APIs, CLIs, databases)
    2. Process data client-side
    3. Return ONLY essential information (not full datasets)
    """
    try:
        # Example: Execute command and process output
        # Replace with actual operation for your skill
        result = subprocess.run([
            "echo", "Performing operation..."
        ], capture_output=True, text=True)

        if result.returncode == 0:
            # Process result client-side
            # Filter, aggregate, or summarize data here
            
            # Return minimal output to context
            print("✓ Operation completed successfully")
            sys.exit(0)
        else:
            # Return concise error message
            print(f"✗ Operation failed: {result.stderr.strip()}")
            sys.exit(1)
            
    except Exception as e:
        print(f"✗ Error during operation: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''

    # Create a sample verification script
    verify_script_content = '''#!/usr/bin/env python3
"""
Verification script - validates operation results.
Returns minimal pass/fail output to the agent.

Usage:
    python verify_operation.py
"""
import sys
import subprocess
import json

def verify():
    """
    Verify the operation results.
    
    This script should:
    1. Check that the operation succeeded
    2. Validate expected outcomes
    3. Return concise status (not full data dumps)
    """
    try:
        # Example: Query system status
        # Replace with actual verification logic
        
        # Perform client-side validation
        checks_passed = True  # Replace with actual checks
        
        if checks_passed:
            print("✓ Verification passed - all checks successful")
            sys.exit(0)
        else:
            print("✗ Verification failed - checks incomplete")
            sys.exit(1)
            
    except Exception as e:
        print(f"✗ Verification error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    verify()
'''

    # Write files
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(skill_content)

    reference_file = skill_dir / "REFERENCE.md"
    reference_file.write_text(reference_content)

    main_script_file = skill_dir / "scripts" / "main_operation.py"
    main_script_file.write_text(main_script_content)
    os.chmod(main_script_file, 0o755)  # Make executable

    verify_script_file = skill_dir / "scripts" / "verify_operation.py"
    verify_script_file.write_text(verify_script_content)
    os.chmod(verify_script_file, 0o755)  # Make executable

    print(f"Created efficient skill '{sanitized_name}' at {skill_dir}")
    print("Directory structure:")
    print(f"  {skill_dir}/")
    print(f"  ├── SKILL.md")
    print(f"  ├── REFERENCE.md")
    print(f"  └── scripts/")
    print(f"      ├── main_operation.py")
    print(f"      └── verify_operation.py")

    return skill_dir


def main():
    if len(sys.argv) < 2:
        print("Usage: python init_skill.py <skill-name> [--path output-directory]")
        print("Example: python init_skill.py 'kubernetes-deployer'")
        sys.exit(1)

    skill_name = sys.argv[1]
    output_dir = "."

    # Check for --path argument
    if "--path" in sys.argv:
        path_index = sys.argv.index("--path") + 1
        if path_index < len(sys.argv):
            output_dir = sys.argv[path_index]

    try:
        skill_dir = create_skill(skill_name, output_dir)
        print(f"\n✓ Efficient skill '{skill_name}' created successfully!")
        print(f"\nThis skill follows MCP Code Execution patterns for optimal token usage:")
        print(f"  - SKILL.md loaded only when triggered (~100 tokens)")
        print(f"  - Scripts execute outside context (0 tokens)")
        print(f"  - REFERENCE.md loaded only if needed (0 tokens upfront)")
        print(f"\nNext steps:")
        print(f"  1. Edit {skill_dir}/SKILL.md:")
        print(f"     - Update description with WHAT and WHEN triggers")
        print(f"     - Customize 'When to Use' scenarios")
        print(f"     - Update instructions and validation checklist")
        print(f"  2. Implement scripts in {skill_dir}/scripts/:")
        print(f"     - main_operation.py: Your primary logic")
        print(f"     - verify_operation.py: Validation checks")
        print(f"     - Ensure minimal output (✓/✗ status only)")
        print(f"  3. Add detailed docs to {skill_dir}/REFERENCE.md")
        print(f"  4. Test with: python scripts/validate_skill.py {skill_dir}")
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()