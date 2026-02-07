# Silver Tier Research Documentation

This document captures technical research, patterns, and decisions made during the implementation of the AI Employee Silver Tier external connectivity features.

## Table of Contents

1. [OAuth2 Authentication Flows](#oauth2-authentication-flows)
2. [WhatsApp Business API Integration](#whatsapp-business-api-integration)
3. [Credential Storage Patterns](#credential-storage-patterns)
4. [SQLite Idempotency Database](#sqlite-idempotency-database)
5. [MCP Server Architecture](#mcp-server-architecture)
6. [Resource Management Strategy](#resource-management-strategy)

---

## OAuth2 Authentication Flows

### Gmail OAuth2

Gmail uses the OAuth 2.0 protocol for authentication with the following flow:

```
┌─────────┐                                  ┌──────────────┐
│  User   │                                  │ Google OAuth │
└────┬────┘                                  └──────┬───────┘
     │  1. Run setup_gmail_oauth.py                │
     │─────────────────────────────────────────────>│
     │                                              │
     │  2. Open browser for consent                 │
     │<─────────────────────────────────────────────│
     │                                              │
     │  3. User grants permissions                  │
     │─────────────────────────────────────────────>│
     │                                              │
     │  4. Authorization code (via localhost)       │
     │<─────────────────────────────────────────────│
     │                                              │
     │  5. Exchange code for tokens                 │
     │─────────────────────────────────────────────>│
     │                                              │
     │  6. Access + Refresh tokens                  │
     │<─────────────────────────────────────────────│
```

**Required Scopes:**
- `https://www.googleapis.com/auth/gmail.readonly` - Read emails
- `https://www.googleapis.com/auth/gmail.send` - Send emails
- `https://www.googleapis.com/auth/gmail.modify` - Modify labels

**Token Storage:**
- Primary: OS credential manager (keytar)
- Fallback: Encrypted file (`~/.ai-employee/credentials.enc`)

**Token Refresh:**
- Access tokens expire after 1 hour
- Refresh automatically when expired (5-minute buffer)
- Refresh tokens are long-lived but can be revoked

### LinkedIn OAuth2

LinkedIn uses OAuth 2.0 with OpenID Connect:

```
┌─────────┐                                  ┌────────────────┐
│  User   │                                  │ LinkedIn OAuth │
└────┬────┘                                  └───────┬────────┘
     │  1. Redirect to authorization URL           │
     │─────────────────────────────────────────────>│
     │                                              │
     │  2. User logs in and grants permissions      │
     │<─────────────────────────────────────────────│
     │                                              │
     │  3. Redirect with authorization code         │
     │─────────────────────────────────────────────>│
     │                                              │
     │  4. Exchange code for tokens                 │
     │<─────────────────────────────────────────────│
```

**Required Scopes:**
- `openid` - User identification
- `profile` - Get user URN for posting
- `w_member_social` - Create posts

**LinkedIn API Endpoints:**
- Token URL: `https://www.linkedin.com/oauth/v2/accessToken`
- User Info: `https://api.linkedin.com/v2/userinfo`
- UGC Posts: `https://api.linkedin.com/v2/ugcPosts`

---

## WhatsApp Business API Integration

### Webhook Architecture

WhatsApp uses a webhook-based architecture for receiving messages:

```
┌───────────┐     ┌─────────────────┐     ┌─────────────────┐
│ WhatsApp  │────>│ Meta Cloud API  │────>│ Your Webhook    │
│   User    │     │                 │     │ (FastAPI)       │
└───────────┘     └─────────────────┘     └─────────────────┘
                                                   │
                                                   v
                                          ┌─────────────────┐
                                          │ Vault           │
                                          │ /Needs_Action   │
                                          └─────────────────┘
```

### Webhook Verification

Meta verifies webhooks using a challenge-response mechanism:

1. Meta sends GET request with `hub.mode`, `hub.challenge`, `hub.verify_token`
2. Server validates `hub.verify_token` matches configured value
3. Server returns `hub.challenge` as plain text
4. Meta confirms webhook is valid

### Signature Validation

All POST requests include `X-Hub-Signature-256` header:

```python
def validate_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        key=secret.encode('utf-8'),
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

### Webhook Payload Structure

```json
{
  "object": "whatsapp_business_account",
  "entry": [{
    "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
    "changes": [{
      "value": {
        "messaging_product": "whatsapp",
        "metadata": {
          "display_phone_number": "+1234567890",
          "phone_number_id": "PHONE_NUMBER_ID"
        },
        "messages": [{
          "from": "1234567890",
          "id": "wamid.HBgLMTIzNDU2Nzg5MBUCAA==",
          "timestamp": "1706187234",
          "type": "text",
          "text": { "body": "Hello!" }
        }]
      }
    }]
  }]
}
```

### Response Time Requirements

Meta requires webhook responses within **20 seconds**, but we target **500ms** to avoid:
- Retry storms
- Message duplication
- Webhook health degradation

Implementation uses background tasks for processing after immediate 200 response.

---

## Credential Storage Patterns

### Storage Hierarchy

```
┌─────────────────────────────────────────────┐
│           OS Credential Manager              │
│  (keytar/keyring - most secure)             │
└──────────────────┬──────────────────────────┘
                   │ Fallback
                   v
┌─────────────────────────────────────────────┐
│         Encrypted File Storage               │
│  (~/.ai-employee/credentials.enc)           │
└──────────────────┬──────────────────────────┘
                   │ Fallback
                   v
┌─────────────────────────────────────────────┐
│         Environment Variables                │
│  (for CI/CD and containers)                 │
└─────────────────────────────────────────────┘
```

### Encryption Details

**Encrypted File Storage:**
- Algorithm: AES-256-CBC
- Key Derivation: SHA-256 of machine ID (`hostname-username`)
- IV: Random 16 bytes, prepended to ciphertext
- Format: `IV (16 bytes) + Ciphertext`

**Machine Key Generation:**
```python
def get_machine_key() -> bytes:
    machine_id = f"{os.hostname()}-{os.userInfo().username}"
    return hashlib.sha256(machine_id.encode()).digest()
```

### Service Names

| Service | Account Key | Description |
|---------|-------------|-------------|
| ai-employee | gmail | Gmail OAuth tokens |
| ai-employee | linkedin | LinkedIn OAuth tokens |

---

## SQLite Idempotency Database

### Schema Design

```sql
-- Processed messages (watcher detections)
CREATE TABLE processed_messages (
    message_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,          -- 'gmail', 'whatsapp', 'file_drop'
    processed_at TEXT NOT NULL,    -- ISO 8601 timestamp
    expires_at TEXT NOT NULL,      -- When to purge
    sender TEXT,                   -- For debugging
    subject TEXT                   -- Preview
);

-- Sent actions (MCP executions)
CREATE TABLE sent_actions (
    action_id TEXT PRIMARY KEY,
    action_type TEXT NOT NULL,     -- 'email', 'linkedin_post'
    recipient TEXT,                -- Target
    sent_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    result_status TEXT NOT NULL,   -- 'success', 'failed'
    error_message TEXT,
    external_id TEXT               -- API-returned ID
);

-- Rate limits
CREATE TABLE rate_limits (
    action_type TEXT NOT NULL,
    limit_date TEXT NOT NULL,      -- YYYY-MM-DD
    current_count INTEGER DEFAULT 0,
    max_count INTEGER NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (action_type, limit_date)
);
```

### Idempotency Key Generation

**Email:**
```python
def generate_email_key(to: str, subject: str, body: str, timestamp: datetime) -> str:
    # Round timestamp to minute to handle slight variations
    rounded = timestamp.replace(second=0, microsecond=0)
    data = json.dumps({
        "to": to.lower().strip(),
        "subject": subject.strip(),
        "body": body.strip(),
        "timestamp": rounded.isoformat()
    })
    return hashlib.sha256(data.encode()).hexdigest()
```

**LinkedIn Post:**
```python
def generate_post_key(content: str, visibility: str, timestamp: datetime) -> str:
    rounded = timestamp.replace(second=0, microsecond=0)
    data = json.dumps({
        "content": content.strip(),
        "visibility": visibility.upper(),
        "timestamp": rounded.isoformat()
    })
    return hashlib.sha256(data.encode()).hexdigest()
```

### Retention Policy

- Default retention: 7 days
- Cleanup runs via weekly scheduled task
- WAL mode enabled for concurrent access

---

## MCP Server Architecture

### Protocol Overview

Model Context Protocol (MCP) provides a standardized way for AI assistants to interact with external tools:

```
┌─────────────┐     stdio      ┌─────────────┐
│   Claude    │<─────────────>│  MCP Server │
│   Desktop   │    JSON-RPC    │  (Gmail)    │
└─────────────┘                └─────────────┘
```

### Tool Registration

```typescript
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [{
    name: "send_email",
    description: "Send an email via Gmail API",
    inputSchema: {
      type: "object",
      properties: {
        to: { type: "string", description: "Recipient" },
        subject: { type: "string" },
        body: { type: "string" }
      },
      required: ["to", "subject", "body"]
    }
  }]
}));
```

### Tool Execution Flow

```
1. Claude calls tool with arguments
2. MCP server validates input (Zod schema)
3. Check rate limits
4. Check idempotency
5. Execute API call
6. Record in idempotency DB
7. Return result to Claude
```

### Error Handling

Standard error codes returned to Claude:
- `RATE_LIMIT_EXCEEDED` - Daily quota reached
- `DUPLICATE_EMAIL` / `DUPLICATE_POST` - Idempotency violation
- `CREDENTIALS_NOT_FOUND` - OAuth not configured
- `TOKEN_EXPIRED` - Refresh failed
- `API_ERROR` - External API failure

---

## Resource Management Strategy

### Memory Budget Allocation

| Process | Budget | Priority |
|---------|--------|----------|
| Gmail Watcher | 100 MB | 1 (High) |
| Approval Watcher | 50 MB | 1 (High) |
| WhatsApp Webhook | 100 MB | 2 (Medium) |
| LinkedIn MCP | 100 MB | 3 (Low) |
| Resource Monitor | 50 MB | - |
| **Total** | **500 MB** | - |

### Graceful Degradation Algorithm

```python
def apply_degradation():
    if total_memory > BUDGET:
        # Pause in priority order (lowest first)
        for watcher in sorted(watchers, key=lambda w: -w.priority):
            if not watcher.paused:
                watcher.pause()
                if total_memory <= BUDGET:
                    break
```

### Recovery Algorithm

```python
def apply_recovery():
    if total_memory < RECOVERY_THRESHOLD:
        # Resume in reverse priority order (highest first)
        for watcher in sorted(watchers, key=lambda w: w.priority):
            if watcher.paused:
                watcher.resume()
```

### State Machine

```
     ┌────────────────────────────────────┐
     │                                    │
     v                                    │
┌─────────┐   >80%    ┌─────────┐   >100%  │
│ NORMAL  │─────────>│ WARNING │─────────>│
└─────────┘           └─────────┘          │
     ^                     │               │
     │     <70%            │               │
     └─────────────────────┘               │
                                           v
                                   ┌──────────┐
                                   │ CRITICAL │
                                   └────┬─────┘
                                        │ pause watchers
                                        v
                                   ┌──────────┐
                                   │ DEGRADED │
                                   └────┬─────┘
                                        │ <70%
                                        │ resume watchers
                                        v
                                   ┌─────────┐
                                   │ NORMAL  │
                                   └─────────┘
```

---

## References

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Gmail API Reference](https://developers.google.com/gmail/api/reference/rest)
- [Meta WhatsApp Business API](https://developers.facebook.com/docs/whatsapp/cloud-api)
- [LinkedIn Marketing API](https://learn.microsoft.com/en-us/linkedin/marketing/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [PM2 Process Manager](https://pm2.keymetrics.io/docs/usage/quick-start/)
