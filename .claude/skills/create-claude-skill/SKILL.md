---
name: create-efficient-skill
description: "WHAT: Creates AI skills using MCP Code Execution pattern for token efficiency. WHEN: User says 'create skill', 'new skill', 'make a skill for', or needs to wrap external system interactions in reusable skills."
---

# Create Efficient Skill

## When to Use
- Creating a new skill for any domain
- Converting direct MCP/API calls to efficient scripts
- Building reusable automation

## Instructions

### 1. Initialize
```bash
python scripts/init_skill.py "skill-name" --path .claude/skills/
```

### 2. Edit SKILL.md
Update the generated file:
- **description**: Include WHAT it does and WHEN to trigger
- **When to Use**: Specific scenarios
- **Instructions**: Script execution commands
- **Validation**: Success criteria

### 3. Implement Scripts
Edit `scripts/main_operation.py` and `scripts/verify_operation.py`:
- Perform operations via subprocess/API calls
- Process data locally
- Return minimal output (e.g., "✓ Done" or "✗ Failed: reason")

### 4. Validate
```bash
python scripts/validate_skill.py .claude/skills/skill-name/
```

## Structure
```
skill-name/
├── SKILL.md              # Instructions (~100 tokens)
├── REFERENCE.md          # Deep docs (on-demand)
└── scripts/
    ├── main_operation.py # Primary logic (0 tokens)
    └── verify_operation.py # Validation (0 tokens)
```

## Validation
- [ ] SKILL.md under 500 lines
- [ ] Description has WHAT and WHEN
- [ ] Scripts return minimal output
- [ ] All scripts executable

See [REFERENCE.md](./REFERENCE.md) for advanced patterns.
