# CEO Weekly Briefing Skill

**WHAT**: Generate comprehensive weekly business briefings for executive review, combining financial data, operational metrics, and AI-generated insights.

**WHEN**: Automatically triggered Sunday 11 PM for Monday delivery. User can also say 'generate CEO briefing', 'weekly summary', 'business audit'. Trigger on: executive reporting, weekly review, business health check.

## Capabilities

### Financial Summary
- Revenue totals from Odoo (collected vs outstanding)
- Invoice and payment activity counts
- Top customers by revenue
- Week-over-week comparison

### Task Metrics
- Completion rates and counts
- Overdue task tracking
- Average completion times
- Productivity trends

### Subscription Health (FR-016)
- Monthly/Annual Recurring Revenue (MRR/ARR)
- Subscription pattern detection
- Churn risk identification
- At-risk customer alerts

### Bottleneck Detection (FR-017)
- Approval workflow delays
- API performance issues
- Queue backup detection
- Overdue task analysis

### AI Suggestions
- Data-driven recommendations
- Priority-ranked action items
- Process improvement suggestions
- Risk mitigation guidance

## Usage Examples

### Generate On-Demand Briefing
```
generate CEO briefing for this week
```

### View Last Briefing
```
show latest CEO briefing
```

### Check Subscription Health
```
analyze subscription patterns
show at-risk customers
```

### Detect Bottlenecks
```
identify workflow bottlenecks
show overdue tasks
```

## Scheduling

The briefing runs automatically on a schedule:

| Event | Time | Description |
|-------|------|-------------|
| Audit | Sunday 11:00 PM | Data collection and analysis |
| Ready | Monday 7:00 AM | Briefing available in vault |
| Delivery | Monday 7:00 AM | Email sent (if configured) |

Configure in `config/gold_tier.yaml`:
```yaml
ceo_briefing:
  schedule: "0 23 * * 0"  # Sunday 11 PM
  timezone: "America/New_York"
  delivery:
    method: email  # or dashboard
    recipient: ceo@company.com
```

## Output Locations

- **Current Briefing**: `vault/CEO_Briefing.md`
- **Dashboard Link**: `vault/Dashboard.md`
- **Archive**: `vault/Archive/briefings/ceo-briefing-YYYY-MM-DD.json`

## Sections

The briefing includes these sections (configurable):

1. **Financial Summary** - Revenue and activity from Odoo
2. **Task Metrics** - Completion rates and workload
3. **Bottlenecks** - Workflow issues and delays
4. **Subscription Health** - Recurring revenue and churn risk
5. **AI Suggestions** - Prioritized recommendations

## Dependencies

- **Odoo MCP**: Financial data (invoices, payments, customers)
- **Task System**: Completion metrics
- **Approval System**: Wait time analysis
- **Subscription Auditor**: MRR/churn analysis
- **Bottleneck Detector**: Workflow analysis

## Error Handling

If data sources are unavailable:
- Briefing generates with available data
- Missing sections marked as "unavailable"
- Errors logged but don't block generation
- Fallback to dashboard if email fails

## Related Skills

- `odoo-ops`: Provides financial data
- `manage-approval`: Provides approval timing
- `view-dashboard`: Shows briefing summary
- `email-ops`: Delivers via email
