---
type: alert
category: odoo
severity: {{ severity }}
created_at: {{ timestamp }}
service: odoo
---

# Odoo Alert: {{ title }}

**Time:** {{ timestamp }}
**Severity:** {{ severity }}

## Issue

{{ description }}

## Error Details

- **Error Code:** {{ error_code }}
- **Operation:** {{ operation }}
- **Message:** {{ error_message }}

## Impact

{{ impact }}

## Recommended Actions

{{ #each actions }}
{{ @index }}. {{ this }}
{{ /each }}

## Context

```json
{{ context_json }}
```

## Auto-Recovery Status

{{ #if auto_recovery_attempted }}
Auto-recovery was attempted: {{ auto_recovery_result }}
{{ else }}
Auto-recovery not applicable for this error type.
{{ /if }}
