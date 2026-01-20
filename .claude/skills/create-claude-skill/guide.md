# Efficient Skill Creation Guide

## Pattern

```
skill-name/
├── SKILL.md              # Loaded when triggered (~100 tokens)
├── REFERENCE.md          # Loaded on-demand (0 tokens upfront)
└── scripts/
    ├── main_operation.py # Executed, not loaded (0 tokens)
    └── verify_operation.py
```

## SKILL.md Format

```yaml
---
name: skill-name
description: "WHAT: [Capability]. WHEN: [Triggers]."
---
```

```markdown
# Skill Name

## When to Use
- [Scenario 1]
- [Scenario 2]

## Instructions
1. `python scripts/main_operation.py [args]`
2. `python scripts/verify_operation.py`

## Validation
- [ ] [Check 1]
- [ ] [Check 2]

See [REFERENCE.md](./REFERENCE.md) for details.
```

## Script Pattern

```python
#!/usr/bin/env python3
import subprocess, json, sys

def main():
    result = subprocess.run(["command"], capture_output=True, text=True)
    data = json.loads(result.stdout)
    
    # Process locally
    summary = process(data)
    
    # Return minimal output
    if success:
        print(f"✓ {summary}")
        sys.exit(0)
    else:
        print(f"✗ {error}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## Available Scripts

### init_skill.py
```bash
python scripts/init_skill.py "skill-name" --path .claude/skills/
```

### validate_skill.py
```bash
python scripts/validate_skill.py /path/to/skill
```

### package_skill.py
```bash
python scripts/package_skill.py /path/to/skill /output.skill
```

## Converting MCP to Skill

**Before (direct MCP):**
```json
{ "servers": { "system": { "command": "mcp-server" } } }
```
Cost: ~15,000 tokens at startup, every session.

**After (skill + script):**
```
.claude/skills/system-ops/
├── SKILL.md
└── scripts/operation.py
```
Cost: ~100 tokens when triggered, 0 otherwise.
