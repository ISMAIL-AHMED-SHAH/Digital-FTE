# Create Efficient AI Skills

This skill helps you create new AI skills with proper structure and MCP Code Execution patterns for optimal efficiency, compatible with Claude Code and Goose (AAIF Standards).

## Purpose

The `create-efficient-skill` skill provides guidance and tools for creating efficient AI skills that use MCP Code Execution patterns to minimize token usage. It includes:

- A template for efficient SKILL.md structure with minimal token usage
- Python scripts to initialize new skills with MCP Code Execution patterns
- Python scripts to package skills for distribution
- Best practices and validation guidelines for efficient skills

## Key Benefits

- **Token Efficiency**: Reduces context usage by 80-98% compared to direct MCP calls
- **Performance**: Moves heavy computation to scripts that execute outside context
- **Scalability**: Enables complex operations without bloating the context window
- **Best Practices**: Follows AAIF standards and MCP Code Execution patterns
- **Cross-Agent Compatibility**: Works seamlessly with Claude Code and Goose

## Usage

When you want to create a new efficient skill, use this skill to:

1. Understand the efficient structure and MCP Code Execution patterns
2. Generate the directory structure with proper separation of concerns
3. Create the initial SKILL.md file with minimal token usage
4. Package the skill for distribution

## Key Components

- `SKILL.md` - Contains the skill definition with minimal metadata and instructions (~100 tokens)
- `REFERENCE.md` - Detailed documentation loaded on-demand
- `scripts/init_skill.py` - Script to initialize a new efficient skill with MCP Code Execution structure
- `scripts/package_skill.py` - Script to package a skill for distribution
- `scripts/validate_skill.py` - Script to validate skills meet efficiency requirements
- `guide.md` - Comprehensive guide to creating efficient skills

## Efficiency Best Practices

- Keep SKILL.md under 500 lines (~100 tokens)
- Move complex operations to scripts in the `scripts/` directory
- Process data client-side in scripts, return minimal output to context
- Use `REFERENCE.md` for detailed documentation that loads on-demand
- Follow MCP Code Execution patterns to minimize token usage
- Test all scripts before packaging