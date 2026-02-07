---
type: alert
category: system
severity: warning
created_at: {{ timestamp }}
---

# Log Size Alert: Storage Threshold Exceeded

**Time:** {{ timestamp }}
**Severity:** Warning

## Issue

Log storage has exceeded {{ threshold_percent }}% of the configured maximum size.

## Current Usage

| Metric | Value |
|--------|-------|
| Current Size | {{ current_size_mb }} MB |
| Maximum Size | {{ max_size_mb }} MB |
| Usage | {{ usage_percent }}% |
| Days Until Full | ~{{ days_until_full }} |

## Largest Log Files

{{ #each large_files }}
| {{ name }} | {{ size_mb }} MB | {{ last_modified }} |
{{ /each }}

## Recommended Actions

### Immediate

1. Run log maintenance manually:
   ```bash
   python -m src.tasks.log_maintenance --compress-now
   ```

2. Archive old logs to external storage

3. Review retention settings in `config/gold_tier.yaml`

### Long-term

1. Consider reducing `retention_days` (currently {{ retention_days }})
2. Enable more aggressive compression
3. Set up log shipping to external storage

## Configuration

Current settings in `config/gold_tier.yaml`:

```yaml
audit:
  log_directory: "{{ log_directory }}"
  retention_days: {{ retention_days }}
  compression_after_days: {{ compression_days }}
  max_size_mb: {{ max_size_mb }}
  alert_threshold_percent: {{ threshold_percent }}
```

## Auto-Maintenance Status

- **Last Run:** {{ last_maintenance_run }}
- **Next Scheduled:** {{ next_maintenance_run }}
- **Compression Enabled:** {{ compression_enabled }}
