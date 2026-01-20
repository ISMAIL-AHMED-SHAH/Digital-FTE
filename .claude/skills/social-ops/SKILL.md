---
name: social-ops
description: "WHAT: Post updates to LinkedIn, schedule posts, and check post status. WHEN: User says 'post to LinkedIn', 'schedule update', 'share business news'. Trigger on: social media marketing, public announcements, lead generation."
---

# Social Operations

## When to Use
- Posting approved updates to LinkedIn
- Scheduling social media posts for future publication
- Checking status of recent posts
- Preventing duplicate content posting

## Instructions
1. **Post Update**:
   ```bash
   python3 .claude/skills/social-ops/scripts/main_operation.py --action post --content "CONTENT"
   ```
   *Note: Requires approval for public posts. Use dry-run to test.*

2. **Schedule Post**:
   ```bash
   python3 .claude/skills/social-ops/scripts/main_operation.py --action schedule --content "CONTENT" --time "ISO8601_TIMESTAMP"
   ```

3. **List Recent Posts**:
   ```bash
   python3 .claude/skills/social-ops/scripts/main_operation.py --action list-recent --limit 5
   ```

## Validation
- [ ] Post successfully published (or logged in dry-run)
- [ ] Duplicate content warning triggered if applicable
- [ ] Audit log entry created

See [REFERENCE.md](./REFERENCE.md) for LinkedIn API configuration.
