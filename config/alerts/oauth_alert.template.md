---
type: alert
category: oauth
severity: critical
created_at: {{ timestamp }}
service: {{ service }}
---

# OAuth Alert: {{ title }}

**Service:** {{ service }}
**Time:** {{ timestamp }}

## Issue

{{ description }}

## Token Status

- **Token Type:** {{ token_type }}
- **Expired:** {{ is_expired }}
- **Last Refresh:** {{ last_refresh }}
- **Error:** {{ error_message }}

## Impact

All {{ service }} operations are paused until token is refreshed.

## Required Actions

1. **Immediate:** Check credential manager for valid tokens
2. **If expired:** Re-authenticate with {{ service }} OAuth flow
3. **Verify:** Run token validation after refresh

## How to Fix

### For Meta (Facebook/Instagram):

```bash
python scripts/setup_meta_oauth.py
```

### For Twitter:

```bash
python scripts/setup_twitter_oauth.py
```

### For Gmail:

```bash
python scripts/setup_gmail_oauth.py
```

## Service Configuration

- **Service:** {{ service }}
- **App ID/Client:** {{ app_id }}
- **Scopes Required:** {{ scopes }}

## Notes

OAuth tokens expire periodically. Set up proactive token refresh by enabling
`oauth.proactive_check: true` in `config/gold_tier.yaml`.
