---
name: social-ops
description: "WHAT: Post updates to LinkedIn, Facebook, Instagram, and Twitter. Schedule posts, check status. WHEN: User says 'post to LinkedIn/Facebook/Instagram', 'schedule update', 'share business news'. Trigger on: social media marketing, public announcements, lead generation."
---

# Social Operations

## When to Use
- Posting approved updates to LinkedIn, Facebook, Instagram, or Twitter
- Scheduling social media posts for future publication
- Checking status of recent posts
- Cross-posting content to multiple platforms
- Preventing duplicate content posting

## Platforms

### LinkedIn (Silver Tier)
- Text posts up to 3000 characters
- Supports PUBLIC and CONNECTIONS visibility
- Requires LinkedIn OAuth credentials

### Facebook (Gold Tier)
- Page posts (text, links, photos)
- Scheduled posts (10 min to 6 months ahead)
- Requires HITL approval by default
- Uses Meta Graph API

### Instagram (Gold Tier)
- Photo, video, reels, and carousel posts
- Caption limit: 2,200 characters, max 30 hashtags
- Requires HITL approval by default
- Uses two-step container workflow

### Twitter (Gold Tier)
- Tweets up to 280 characters
- Thread support for longer content
- Requires HITL approval by default

## Instructions

### 1. Post to LinkedIn
```bash
python3 .claude/skills/social-ops/scripts/main_operation.py --action post --platform linkedin --content "CONTENT"
```

### 2. Post to Facebook
```bash
python3 .claude/skills/social-ops/scripts/main_operation.py --action post --platform facebook --page-id PAGE_ID --content "CONTENT"
```

### 3. Post to Instagram
```bash
python3 .claude/skills/social-ops/scripts/main_operation.py --action post --platform instagram --account-id ACCOUNT_ID --image-url URL --caption "CAPTION"
```

### 4. Schedule Post
```bash
python3 .claude/skills/social-ops/scripts/main_operation.py --action schedule --platform facebook --page-id PAGE_ID --content "CONTENT" --time "2026-02-10T09:00:00Z"
```

### 5. Cross-Post to Multiple Platforms
```bash
python3 .claude/skills/social-ops/scripts/main_operation.py --action cross-post --platforms linkedin,facebook --content "CONTENT"
```

### 6. List Recent Posts
```bash
python3 .claude/skills/social-ops/scripts/main_operation.py --action list-recent --platform all --limit 5
```

### 7. Check Platform Status
```bash
python3 .claude/skills/social-ops/scripts/main_operation.py --action status
```

## HITL Approval Workflow (Gold Tier)

For Facebook, Instagram, and Twitter posts, the default workflow requires human approval:

1. **Create draft**: AI creates approval file in `vault/Needs_Action/`
2. **Review**: Human reviews the post content
3. **Approve**: Move file to `vault/Done/` to publish
4. **Reject**: Move file to `vault/Rejected/` with reason

To skip approval (use with caution):
```bash
python3 .claude/skills/social-ops/scripts/main_operation.py --action post --platform facebook --no-approval --content "CONTENT"
```

## Validation
- [ ] Post successfully published (or logged in dry-run)
- [ ] Approval file created for Gold Tier platforms
- [ ] Duplicate content warning triggered if applicable
- [ ] Character/hashtag limits validated
- [ ] Audit log entry created

## Environment Variables

| Variable | Platform | Description |
|----------|----------|-------------|
| `LINKEDIN_ACCESS_TOKEN` | LinkedIn | OAuth access token |
| `META_APP_ID` | Facebook/Instagram | Meta App ID |
| `META_APP_SECRET` | Facebook/Instagram | Meta App Secret |
| `META_ACCESS_TOKEN` | Facebook/Instagram | Page access token |
| `META_PAGE_ID` | Facebook | Default Page ID |
| `META_INSTAGRAM_ID` | Instagram | Default Instagram Business Account ID |
| `TWITTER_API_KEY` | Twitter | Twitter API Key |
| `TWITTER_API_SECRET` | Twitter | Twitter API Secret |
| `TWITTER_ACCESS_TOKEN` | Twitter | Twitter Access Token |
| `TWITTER_ACCESS_SECRET` | Twitter | Twitter Access Token Secret |

## Rate Limits

| Platform | Limit | Window |
|----------|-------|--------|
| LinkedIn | 100 posts | 24 hours |
| Facebook | 4800 calls | 24 hours |
| Instagram | 25 posts | 24 hours |
| Twitter | 300 tweets | 3 hours |

## Related Skills
- `email-ops`: For email communications
- `ceo-briefing`: For social metrics in briefings
- `manage-approval`: For HITL approval workflow

See [REFERENCE.md](./REFERENCE.md) for detailed API configuration.
