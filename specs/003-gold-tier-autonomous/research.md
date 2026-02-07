# Research: Gold Tier - Autonomous Employee

**Date**: 2026-02-05
**Purpose**: Document research findings for Gold Tier implementation technologies

---

## 1. Odoo Community JSON-RPC API (v19+)

### Authentication

**Recommended**: API Key Authentication (v14+)
- Generate from Odoo user profile settings
- Replace password with API key in requests
- More secure (can be revoked independently)

**Authentication Endpoint**: `POST /jsonrpc` with `common/authenticate`

### Invoice Creation

**Model**: `account.move`
**Key Fields**:
- `move_type`: `out_invoice` (customer invoice)
- `partner_id`: Customer/partner ID
- `invoice_date`: Date string (YYYY-MM-DD)
- `invoice_line_ids`: Array of `(0, 0, {line_data})` tuples

```python
invoice_data = {
    'move_type': 'out_invoice',
    'partner_id': customer_id,
    'invoice_date': '2026-02-05',
    'invoice_line_ids': [
        (0, 0, {'name': 'Service', 'quantity': 1, 'price_unit': 100.00})
    ]
}
invoice_id = client.call('account.move', 'create', [invoice_data])
```

### Payment Creation

**Model**: `account.payment`
**Workflow**: Create → Post → Reconcile

```python
payment_data = {
    'payment_type': 'inbound',  # or 'outbound'
    'partner_id': partner_id,
    'amount': 100.00,
    'journal_id': 1,  # Cash/Bank journal
}
payment_id = client.call('account.payment', 'create', [payment_data])
client.call('account.payment', 'action_post', [payment_id])
```

### Financial Queries

**Revenue Query**:
```python
invoices = client.call('account.move', 'search_read', [
    [('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]
], {'fields': ['amount_total', 'amount_residual', 'partner_id']})
```

### Error Handling

| Error Code | Meaning | Action |
|------------|---------|--------|
| -32097 | Access Denied | Check permissions |
| -32098 | Validation Error | Check field constraints |
| -32500 | Server Error | Retry with backoff |

### Connection Management

- Use `requests.Session` for connection pooling
- 30-second timeout (per spec clarification)
- 3 retries with exponential backoff
- Queue locally after retries exhaust

---

## 2. Meta Business Suite API (Graph API v22+)

### OAuth2 Authentication

**Token Types**:
- **User Access Token**: Short-lived (~2 hours)
- **Page Access Token**: Long-lived (for posting)
- **System User Token**: App-only flows (recommended for MCP)

**Required Scopes**:
- `pages_manage_posts` - Post to Pages
- `pages_read_engagement` - Read analytics
- `instagram_basic` - Instagram access
- `instagram_content_publishing` - Post to Instagram

### Facebook Pages Posting

**Endpoint**: `POST /{page-id}/feed`

```typescript
const response = await axios.post(
  `https://graph.facebook.com/v22.0/${pageId}/feed`,
  {
    message: 'Post content',
    access_token: pageAccessToken
  }
);
```

**Parameters**:
- `message`: Text content
- `link`: URL to share
- `picture`: Image URL
- `scheduled_publish_time`: Unix timestamp for scheduling

### Instagram Publishing

**Two-Step Process**:
1. Create container: `POST /{ig-user-id}/media`
2. Publish: `POST /{ig-user-id}/media_publish`

```typescript
// Step 1: Create container
const container = await axios.post(
  `https://graph.instagram.com/v22.0/${igUserId}/media`,
  { image_url: imageUrl, caption: caption }
);

// Step 2: Wait for processing
// ...poll status until FINISHED

// Step 3: Publish
const published = await axios.post(
  `https://graph.instagram.com/v22.0/${igUserId}/media_publish`,
  { creation_id: container.data.id }
);
```

### Rate Limits

| Platform | Limit |
|----------|-------|
| Facebook Pages | 200 requests/hour (standard tier) |
| Instagram | 50 posts/24 hours |

### Token Refresh Strategy

**Proactive Refresh** (per spec clarification):
- Check token expiry before each API call
- Refresh if <1 hour remaining
- Use `fb_exchange_token` grant type

---

## 3. Twitter API v2

### Authentication

**For Posting**: OAuth 1.0a REQUIRED
- Cannot post with Bearer tokens (read-only)
- Requires: API Key, API Secret, Access Token, Access Token Secret

**Alternative**: OAuth 2.0 Authorization Code Flow with PKCE
- User delegation with `tweet.write` scope
- Note: Media upload still requires OAuth 1.0a fallback

### Tweet Posting

**Endpoint**: `POST https://api.x.com/2/tweets`

```typescript
import { TwitterApi } from 'twitter-api-v2';

const client = new TwitterApi({
  appKey: process.env.TWITTER_API_KEY,
  appSecret: process.env.TWITTER_API_SECRET,
  accessToken: process.env.TWITTER_ACCESS_TOKEN,
  accessSecret: process.env.TWITTER_ACCESS_SECRET,
});

const { data } = await client.v2.tweet('Hello, World!');
```

### Character Limits

- **Standard tweet**: 280 characters
- No automatic truncation - validate client-side
- Thread handling via `reply.in_reply_to_tweet_id`

### Rate Limits

| Operation | Limit |
|-----------|-------|
| Create Tweet | 100 per 15 minutes (per user) |
| Delete Tweet | 50 per 15 minutes |
| App-level | 10,000 posts per 24 hours |

### Media Upload

Media upload uses v1 API (v2 not available):
```typescript
const mediaId = await client.v1.uploadMedia('./image.jpg');
await client.v2.tweet('Check this out!', {
  media: { media_ids: [mediaId] }
});
```

---

## 4. Claude Code Stop Hooks (Ralph Wiggum Pattern)

### Hook Configuration

**Location**: `.claude/settings.json` or `.claude/plugins/ralph-wiggum/hooks/hooks.json`

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/ralph-wiggum-stop.sh"
          }
        ]
      }
    ]
  }
}
```

### Hook Input Schema

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/current/working/directory",
  "stop_hook_active": true/false
}
```

### Exit Codes

| Code | Meaning | Effect |
|------|---------|--------|
| 0 | Task complete | Allow Claude to exit |
| 2 | Task incomplete | Block exit, continue loop |

### Completion Detection Strategies

**1. Promise-Based**:
```bash
if grep -q "<promise>TASK_COMPLETE</promise>" "$TRANSCRIPT"; then
  exit 0  # Complete
fi
exit 2  # Continue
```

**2. File-Based**:
```bash
if [ -f "/vault/Done/task.md" ]; then
  exit 0  # Complete (file moved to Done)
fi
exit 2  # Continue
```

**3. Hybrid** (Recommended):
- Primary: Check if task file moved to /Done
- Secondary: Check for promise in transcript
- Tertiary: Max iterations guard

### Infinite Loop Prevention

1. **Max Iterations**: Default 10, configurable via `--max-iterations`
2. **Stop Hook Active Flag**: `stop_hook_active` prevents recursion
3. **Stagnation Detection**: No progress in 3 iterations → escalate
4. **Timeout**: 30 minutes max per loop

### Context Persistence

Context persists automatically through:
- Modified files (visible via Read tool)
- Git diffs (show what changed)
- Transcript history (available to hook)

No explicit context re-injection needed - Claude sees its previous work.

---

## 5. Implementation Recommendations

### Odoo MCP Server

- Use Python `requests` with connection pooling
- Store API key in OS credential manager
- Implement 30-second timeout, 3 retries
- Queue operations locally on failure
- All actions create drafts (require approval)

### Meta MCP Servers

- Separate Facebook and Instagram MCPs
- Proactive OAuth token refresh (<1 hour threshold)
- Rate limit tracking per platform
- Two-step Instagram publishing workflow

### Twitter MCP Server

- Use `twitter-api-v2` npm package
- OAuth 1.0a for all posting operations
- Validate 280 char limit before API call
- Queue posts when rate limited

### Ralph Wiggum Loop

- Hybrid completion strategy (file + promise)
- Max 10 iterations default
- Log each iteration
- Generate summary on completion or max reached

---

## Sources

- [Odoo 19 External API Documentation](https://www.odoo.com/documentation/19.0/developer/reference/external_api.html)
- [Meta Graph API Documentation](https://developers.facebook.com/docs/graph-api/)
- [Instagram Content Publishing API](https://developers.facebook.com/docs/instagram-api/guides/content-publishing/)
- [Twitter API v2 Documentation](https://docs.x.com/x-api/posts/create-post)
- [Claude Code Hooks Reference](https://code.claude.com/docs/en/hooks)
- [Ralph Wiggum Pattern Blog Post](https://paddo.dev/blog/ralph-wiggum-autonomous-loops/)
