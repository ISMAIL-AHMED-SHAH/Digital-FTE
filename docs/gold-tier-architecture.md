# Gold Tier Architecture

## Overview

The Gold Tier "Autonomous Employee" builds upon Bronze and Silver tiers to provide:

1. **Odoo ERP Integration** - Full accounting automation
2. **Multi-Platform Social Media** - Facebook, Instagram, Twitter
3. **Ralph Wiggum Loop** - Autonomous multi-step task execution
4. **Error Recovery** - Graceful degradation and auto-recovery
5. **Comprehensive Audit Logging** - Full action tracking

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AI Employee System                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │ File Watcher │    │  Orchestrator │    │   Watchdog   │          │
│  │   (Bronze)   │───▶│   (Silver)    │◀───│   (Gold)     │          │
│  └──────────────┘    └──────────────┘    └──────────────┘          │
│         │                   │                    │                  │
│         ▼                   ▼                    ▼                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                      MCP Server Layer                        │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │   │
│  │  │  Odoo   │ │Facebook │ │Instagram│ │ Twitter │           │   │
│  │  │   MCP   │ │   MCP   │ │   MCP   │ │   MCP   │           │   │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘           │   │
│  └───────┼───────────┼───────────┼───────────┼────────────────┘   │
│          │           │           │           │                     │
│          ▼           ▼           ▼           ▼                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   External Services                          │   │
│  │  ┌─────────┐ ┌─────────────┐ ┌────────────────┐             │   │
│  │  │  Odoo   │ │ Meta Graph  │ │  Twitter API   │             │   │
│  │  │ JSON-RPC│ │   API v18   │ │     v2         │             │   │
│  │  └─────────┘ └─────────────┘ └────────────────┘             │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                     Support Systems                          │   │
│  │  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────┐   │   │
│  │  │   Audit   │ │   Error   │ │   Action  │ │ Quarantine│   │   │
│  │  │  Logger   │ │Categorizer│ │   Queue   │ │  Handler  │   │   │
│  │  └───────────┘ └───────────┘ └───────────┘ └───────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Component Interactions

### 1. Task Processing Flow

```
Drop Folder → File Watcher → Needs_Action → HITL Approval → MCP Execution → Done
                    │                              │               │
                    └──────────────────────────────┼───────────────┘
                                                   │
                                           Audit Logger
```

### 2. Ralph Wiggum Loop

```
Start Loop → Check Completion → Execute Step → Record Action → Check Stop
     ↑              │                                             │
     │              ├─ File moved to Done? ──────────────────────▶│
     │              ├─ Promise fulfilled? ───────────────────────▶│
     │              ├─ Max iterations? ──────────────────────────▶│
     │              ├─ Error threshold? ─────────────────────────▶│
     │              └─ Approval pending? ────────────────────────▶│
     │                                                             │
     └──────────────────── Continue ◀──────────────────────────────┘
```

### 3. Error Recovery Flow

```
API Error → Error Categorizer → Strategy Selection
                                      │
            ┌─────────────────────────┼─────────────────────────┐
            │                         │                         │
      ┌─────▼─────┐            ┌─────▼─────┐            ┌─────▼─────┐
      │ TRANSIENT │            │   AUTH    │            │   DATA    │
      │  Retry    │            │  Pause &  │            │Quarantine │
      │  w/Backoff│            │  Alert    │            │           │
      └───────────┘            └───────────┘            └───────────┘
```

## Data Flow

### Vault Structure (Gold Tier Additions)

```
vault/
├── Drop/                   # Input folder (Bronze)
├── Needs_Action/           # Pending HITL approval (Silver)
├── Done/                   # Completed tasks (Bronze)
├── Quarantine/             # Failed files (Gold)
├── Alerts/                 # System alerts (Gold)
├── Briefings/              # CEO briefings (Gold)
├── Logs/                   # Audit logs (Gold)
│   ├── 2026-02-01.json
│   ├── 2026-02-02.json.gz
│   └── ...
└── Archive/
    └── loop_summaries/     # Ralph execution summaries
```

### State Files

```
data/
├── action_queue.json       # Graceful degradation queue
├── watchdog/
│   └── watchdog_state.json # Process monitor state
└── ralph/
    └── {task_id}_state.json # Loop execution state
```

## MCP Server Architecture

### Odoo MCP

```
src/mcp_servers/odoo/
├── package.json
├── src/
│   ├── index.ts            # Entry point
│   ├── lib/
│   │   └── odoo_client.ts  # JSON-RPC client
│   └── tools/
│       ├── create_invoice.ts
│       ├── create_payment.ts
│       └── get_financial_summary.ts
└── dist/                   # Compiled output
```

### Social Media MCPs

```
src/mcp_servers/
├── facebook/
│   └── src/
│       ├── lib/meta_oauth.ts   # Shared OAuth
│       └── tools/create_post.ts
├── instagram/
│   └── src/
│       └── tools/publish_media.ts
└── twitter/
    └── src/
        ├── lib/twitter_client.ts
        └── tools/post_tweet.ts
```

## Security Architecture

### Credential Management

```
┌─────────────────────────────────────────────────────────┐
│                    Credential Flow                       │
│                                                          │
│  .env File ──▶ OS Environment ──▶ Credential Manager    │
│                                          │               │
│                                          ▼               │
│                              ┌──────────────────────┐   │
│                              │   Service Clients    │   │
│                              │ (Odoo, Meta, Twitter)│   │
│                              └──────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### HITL Approval Flow

```
1. MCP receives action request
2. Check if HITL required (Gold Tier platforms)
3. Create approval file in Needs_Action
4. Wait for human approval (file rename/move)
5. Execute only after approval
6. Log all steps in audit
```

## Process Management

### PM2 Ecosystem

```javascript
// ecosystem.config.js
{
  apps: [
    { name: 'file-watcher',  autorestart: true, max_restarts: 10 },
    { name: 'odoo-mcp',      autorestart: true, max_restarts: 5 },
    { name: 'facebook-mcp',  autorestart: true, max_restarts: 5 },
    { name: 'instagram-mcp', autorestart: true, max_restarts: 5 },
    { name: 'twitter-mcp',   autorestart: true, max_restarts: 5 },
    { name: 'action-queue',  autorestart: true, max_restarts: 10 },
    { name: 'watchdog',      autorestart: true, max_restarts: 3 },
  ]
}
```

### Watchdog Monitoring

The watchdog monitors all processes and:
- Detects crashes via PM2 status
- Auto-restarts with cooldown
- Generates alerts on repeated failures
- Persists state for crash recovery

## Configuration

### gold_tier.yaml Structure

```yaml
ceo_briefing:
  schedule: { day: 0, time: "23:00" }

rate_limits:
  facebook: { posts_per_day: 5 }
  instagram: { posts_per_day: 3 }
  twitter: { tweets_per_day: 50 }

ralph_wiggum:
  max_iterations: 50
  timeout_minutes: 30
  completion_strategy: hybrid

error_recovery:
  retry: { max_attempts: 5, backoff_multiplier: 2 }
  graceful_degradation: { enabled: true }

audit:
  retention_days: 90
  compression_after_days: 30
```

## Performance Considerations

### Target Metrics

| Operation | Target | Actual |
|-----------|--------|--------|
| Odoo invoice creation | < 5s | TBD |
| Social post (from approval) | < 5min | TBD |
| Loop iteration | < 30s | TBD |
| Log query (30 days) | < 10s | TBD |

### Optimization Strategies

1. **Connection pooling** for Odoo JSON-RPC
2. **Rate limit awareness** for social APIs
3. **Compressed log queries** for older data
4. **Async operations** where possible

## Scalability

### Current Limits

- Single vault instance
- One file watcher per vault
- Sequential MCP execution
- PM2 on single host

### Future Considerations

- Multi-vault support
- Distributed file watching
- MCP load balancing
- Container orchestration
