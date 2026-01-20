#!/usr/bin/env python3
"""
Script to validate a Claude Code skill meets the required standards.
"""

import os
import sys
import yaml
from pathlib import Path
import re


def validate_skill(skill_path):
    """
    Validate a Claude Code skill meets the required standards.
    
    Args:
        skill_path (str or Path): Path to the skill directory
    """
    skill_dir = Path(skill_path)
    
    print(f"Validating skill at: {skill_dir}")
    
    # Check if SKILL.md exists
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        print("❌ FAIL: SKILL.md file not found")
        return False
    
    # Read SKILL.md content
    content = skill_file.read_text()
    
    # Check for YAML frontmatter
    if not content.startswith("---\n"):
        print("❌ FAIL: Missing YAML frontmatter (---)")
        return False
    
    # Extract YAML frontmatter
    parts = content.split("---", 2)
    if len(parts) < 3:
        print("❌ FAIL: Invalid YAML frontmatter format")
        return False
    
    yaml_content = parts[1]
    
    try:
        metadata = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        print(f"❌ FAIL: Invalid YAML in frontmatter: {e}")
        return False
    
    # Validate required fields
    if not metadata.get('name'):
        print("❌ FAIL: Missing 'name' field in frontmatter")
        return False
    
    if not metadata.get('description'):
        print("❌ FAIL: Missing 'description' field in frontmatter")
        return False
    
    # Validate name format
    name = metadata['name']
    if len(name) > 64:
        print(f"❌ FAIL: Name too long ({len(name)} > 64 characters)")
        return False
    
    if not re.match(r'^[a-z0-9][a-z0-9\-]*[a-z0-9]$', name) and name != name.lower():
        print(f"❌ FAIL: Name should be lowercase with hyphens only: {name}")
        return False
    
    # Validate description
    description = metadata['description']
    if len(description) > 1024:
        print(f"❌ FAIL: Description too long ({len(description)} > 1024 characters)")
        return False
    
    if 'WHAT' not in description and 'WHEN' not in description:
        print("⚠️  WARNING: Description should include both WHAT and WHEN for proper triggering")
    
    # Check SKILL.md length
    lines = content.split('\n')
    if len(lines) > 500:
        print(f"⚠️  WARNING: SKILL.md has {len(lines)} lines, consider keeping under 500")
    
    # Check for required directories
    scripts_dir = skill_dir / "scripts"
    reference_file = skill_dir / "REFERENCE.md"
    
    if not scripts_dir.exists():
        print("⚠️  INFO: scripts/ directory not found (optional)")
    else:
        print("✅ Found scripts/ directory")
    
    if not reference_file.exists():
        print("⚠️  INFO: REFERENCE.md file not found (optional)")
    else:
        print("✅ Found REFERENCE.md file")
    
    print("✅ Basic validation passed")
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_skill.py <path/to/skill-directory>")
        print("Example: python validate_skill.py ./my-skill")
        sys.exit(1)
    
    skill_path = sys.argv[1]
    
    try:
        is_valid = validate_skill(skill_path)
        if is_valid:
            print("\n🎉 Skill validation completed successfully!")
        else:
            print("\n💥 Skill validation failed!")
            sys.exit(1)
    except Exception as e:
        print(f"Error validating skill: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()