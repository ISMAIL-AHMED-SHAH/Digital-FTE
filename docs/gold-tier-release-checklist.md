# Gold Tier Release Checklist

## Pre-Release Verification

### Configuration
- [ ] `config/gold_tier.yaml` reviewed and values appropriate
- [ ] `.env` file has all required credentials (not committed)
- [ ] PM2 ecosystem.config.js reviewed

### Security
- [ ] No credentials in source code
- [ ] All API keys in environment variables or credential manager
- [ ] `.env` in `.gitignore`
- [ ] OAuth tokens stored securely
- [ ] Sensitive data redacted in logs

### Dependencies
- [ ] Python dependencies in `requirements.txt` are pinned
- [ ] Node.js dependencies locked in `package-lock.json`
- [ ] All MCP servers have their own `package.json`

### Testing
- [ ] Unit tests pass: `pytest tests/unit/`
- [ ] Integration tests pass: `pytest tests/integration/`
- [ ] Manual smoke test completed

## Component Verification

### Odoo Integration
- [ ] Connection test passes
- [ ] Invoice creation works
- [ ] Payment creation works
- [ ] Financial summary returns data
- [ ] Error handling tested

### Social Media
- [ ] Facebook OAuth configured
- [ ] Facebook post creation works
- [ ] Instagram OAuth configured
- [ ] Instagram media publishing works
- [ ] Twitter OAuth configured
- [ ] Twitter posting works
- [ ] HITL approval workflow tested for all platforms

### Ralph Wiggum Loop
- [ ] Loop starts correctly
- [ ] Completion detection works (file-based)
- [ ] Completion detection works (promise-based)
- [ ] Max iterations limit works
- [ ] Error threshold limit works
- [ ] Summary generation works

### Error Recovery
- [ ] Transient errors retry with backoff
- [ ] Auth errors generate alerts
- [ ] Data errors quarantine files
- [ ] Graceful degradation queue works
- [ ] Watchdog restarts crashed processes

### Audit Logging
- [ ] All actions logged to vault/Logs
- [ ] Log query works
- [ ] Log compression works (30+ days)
- [ ] Log cleanup works (90+ days)
- [ ] Size alerting works

## Documentation
- [ ] Architecture diagram current
- [ ] Troubleshooting guide complete
- [ ] API credentials setup documented
- [ ] CLAUDE.md updated with Gold Tier skills

## Operational Readiness

### Monitoring
- [ ] PM2 monitoring configured
- [ ] Watchdog alerts configured
- [ ] Log size monitoring enabled

### Backup
- [ ] Vault backup strategy documented
- [ ] State file backup included
- [ ] Config backup strategy

### Recovery
- [ ] Graceful degradation tested
- [ ] Manual recovery procedures documented
- [ ] Rollback procedure documented

## Deployment Steps

### 1. Pre-Deployment
```bash
# Backup current state
cp -r vault vault.backup
cp -r data data.backup

# Pull latest code
git pull origin main

# Install dependencies
pip install -r requirements.txt
cd src/mcp_servers && npm install
```

### 2. Configuration
```bash
# Copy environment template
cp config/.env.example .env

# Edit .env with actual credentials
# Set ODOO_*, META_*, TWITTER_* variables
```

### 3. Build MCP Servers
```bash
cd src/mcp_servers/odoo && npm run build
cd ../facebook && npm run build
cd ../instagram && npm run build
cd ../twitter && npm run build
```

### 4. Start Services
```bash
# Start all services
pm2 start ecosystem.config.js

# Verify status
pm2 status

# Check logs
pm2 logs --lines 50
```

### 5. Post-Deployment Verification
```bash
# Test Odoo connection
python scripts/setup_odoo_connection.py --test

# Test social OAuth
python scripts/setup_meta_oauth.py --verify
python scripts/setup_twitter_oauth.py --verify

# Check dashboard
python -m src.skills.view_dashboard
```

## Rollback Procedure

If issues arise:

```bash
# Stop all services
pm2 stop all

# Restore backups
rm -rf vault && mv vault.backup vault
rm -rf data && mv data.backup data

# Restart with previous version
git checkout <previous-tag>
pm2 start ecosystem.config.js
```

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Developer | | | |
| Reviewer | | | |
| QA | | | |

---

**Release Version:** 1.0.0-gold
**Release Date:** ___________
**Release Notes:** See CHANGELOG.md
