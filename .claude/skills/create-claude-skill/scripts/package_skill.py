
#!/usr/bin/env python3
"""
Script to package a Claude Code skill into a distributable .skill file.
"""

import os
import sys
import zipfile
from pathlib import Path


def package_skill(skill_path, output_path=None):
    """
    Package a Claude Code skill into a distributable .skill file.
    
    Args:
        skill_path (str or Path): Path to the skill directory
        output_path (str or Path, optional): Path for the output .skill file
    """
    skill_dir = Path(skill_path)
    
    if not skill_dir.exists():
        raise FileNotFoundError(f"Skill directory does not exist: {skill_dir}")
    
    if not (skill_dir / "SKILL.md").exists():
        raise FileNotFoundError(f"SKILL.md not found in {skill_dir}")
    
    # Determine output path
    if output_path is None:
        output_path = f"{skill_dir.name}.skill"
    else:
        output_path = Path(output_path)
        if output_path.is_dir():
            output_path = output_path / f"{skill_dir.name}.skill"
    
    # Create the zip file
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(skill_dir):
            for file in files:
                file_path = Path(root) / file
                # Add file to zip with relative path
                arcname = file_path.relative_to(skill_dir.parent)
                zipf.write(file_path, arcname)
    
    print(f"Skill packaged successfully: {output_path}")
    return output_path


def main():
    if len(sys.argv) < 2:
        print("Usage: python package_skill.py <path/to/skill-directory> [output-path]")
        print("Example: python package_skill.py ./my-skill ./dist/my-skill.skill")
        sys.exit(1)
    
    skill_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        package_path = package_skill(skill_path, output_path)
        print(f"Skill has been packaged to: {package_path}")
    except Exception as e:
        print(f"Error packaging skill: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()