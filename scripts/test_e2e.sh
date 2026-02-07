#!/bin/bash
# =============================================================================
# End-to-End Test Script for AI Employee Silver Tier
# =============================================================================
#
# This script tests the complete system flow in dry-run mode:
# 1. WhatsApp webhook endpoint
# 2. Gmail MCP server
# 3. LinkedIn MCP server
# 4. Vault file operations
# 5. Resource monitor
#
# Usage:
#   ./scripts/test_e2e.sh [--verbose]
#
# Environment:
#   DRY_RUN=true is automatically set for all tests
#
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VERBOSE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

log_verbose() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}[DEBUG]${NC} $1"
    fi
}

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# Track test result
pass_test() {
    ((TESTS_PASSED++))
    log_success "$1"
}

fail_test() {
    ((TESTS_FAILED++))
    log_error "$1"
}

skip_test() {
    ((TESTS_SKIPPED++))
    log_warn "SKIPPED: $1"
}

# =============================================================================
# Test Functions
# =============================================================================

test_python_imports() {
    log_info "Testing Python module imports..."

    cd "$PROJECT_ROOT"
    export DRY_RUN=true

    # Test core modules
    modules=(
        "src.common.vault"
        "src.common.audit_logger"
        "src.common.idempotency"
        "src.common.integrity"
        "src.watchers.base_watcher"
        "src.watchers.resource_monitor"
        "src.watchers.scheduler"
        "src.tasks.daily_briefing"
    )

    for module in "${modules[@]}"; do
        if python -c "import $module" 2>/dev/null; then
            pass_test "Import: $module"
        else
            fail_test "Import: $module"
        fi
    done
}

test_vault_operations() {
    log_info "Testing vault operations in dry-run mode..."

    cd "$PROJECT_ROOT"
    export DRY_RUN=true

    # Test vault initialization
    python -c "
from src.common.vault import get_vault
vault = get_vault()
print(f'Vault path: {vault.vault_path}')
print(f'Folders configured: {list(vault.folders.keys())}')
" && pass_test "Vault initialization" || fail_test "Vault initialization"

    # Test vault file listing
    python -c "
from src.common.vault import get_vault
vault = get_vault()
files = vault.list_files('needs_action', '*.md')
print(f'Action files found: {len(files)}')
" && pass_test "Vault file listing" || fail_test "Vault file listing"
}

test_idempotency_db() {
    log_info "Testing idempotency database..."

    cd "$PROJECT_ROOT"
    export DRY_RUN=true

    python -c "
from src.common.idempotency import get_idempotency_db

db = get_idempotency_db()

# Test message processing check
is_processed = db.is_processed('test-message-123', 'test')
print(f'Test message processed: {is_processed}')

# Test stats
stats = db.get_stats()
print(f'DB stats: {stats}')
" && pass_test "Idempotency database" || fail_test "Idempotency database"
}

test_audit_logger() {
    log_info "Testing audit logger..."

    cd "$PROJECT_ROOT"
    export DRY_RUN=true

    python -c "
from src.common.audit_logger import get_audit_logger

logger = get_audit_logger()

# Test logging (dry-run should not write to disk)
logger.log_detection(
    component='test',
    action_type='e2e_test',
    target='test_target',
    parameters={'dry_run': True}
)
print('Audit log entry created (dry-run)')
" && pass_test "Audit logger" || fail_test "Audit logger"
}

test_resource_monitor() {
    log_info "Testing resource monitor..."

    cd "$PROJECT_ROOT"
    export DRY_RUN=true

    python -c "
from src.watchers.resource_monitor import ResourceMonitor

monitor = ResourceMonitor(dry_run=True)

# Test memory monitoring
usage = monitor.get_memory_usage()
print(f'Current memory usage: {usage}')

# Test budget check
exceeds = monitor.exceeds_budget()
print(f'Exceeds budget: {exceeds}')

# Test stats
stats = monitor.get_stats()
print(f'Monitor stats: {stats}')
" && pass_test "Resource monitor" || fail_test "Resource monitor"
}

test_scheduler() {
    log_info "Testing scheduler..."

    cd "$PROJECT_ROOT"
    export DRY_RUN=true

    python -c "
from src.watchers.scheduler import TaskScheduler

scheduler = TaskScheduler(dry_run=True)

# Test task listing
tasks = scheduler.list_tasks()
print(f'Configured tasks: {list(tasks.keys())}')
" && pass_test "Scheduler" || fail_test "Scheduler"
}

test_whatsapp_webhook_syntax() {
    log_info "Testing WhatsApp webhook syntax..."

    cd "$PROJECT_ROOT"

    # Just test that the module parses correctly
    python -c "
import ast
with open('src/watchers/whatsapp_webhook.py', 'r') as f:
    ast.parse(f.read())
print('WhatsApp webhook syntax valid')
" && pass_test "WhatsApp webhook syntax" || fail_test "WhatsApp webhook syntax"
}

test_gmail_mcp_typescript() {
    log_info "Testing Gmail MCP TypeScript..."

    cd "$PROJECT_ROOT/src/mcp_servers/gmail"

    if command -v npx &> /dev/null; then
        if npx tsc --noEmit 2>/dev/null; then
            pass_test "Gmail MCP TypeScript compilation"
        else
            fail_test "Gmail MCP TypeScript compilation"
        fi
    else
        skip_test "Gmail MCP TypeScript (npx not available)"
    fi
}

test_linkedin_mcp_typescript() {
    log_info "Testing LinkedIn MCP TypeScript..."

    cd "$PROJECT_ROOT/src/mcp_servers/linkedin"

    if command -v npx &> /dev/null; then
        if [ -d "node_modules" ]; then
            if npx tsc --noEmit 2>/dev/null; then
                pass_test "LinkedIn MCP TypeScript compilation"
            else
                fail_test "LinkedIn MCP TypeScript compilation"
            fi
        else
            skip_test "LinkedIn MCP TypeScript (node_modules not installed)"
        fi
    else
        skip_test "LinkedIn MCP TypeScript (npx not available)"
    fi
}

test_config_files() {
    log_info "Testing configuration files..."

    cd "$PROJECT_ROOT"

    # Test YAML config parsing
    if [ -f "config/watcher_config.yaml" ]; then
        python -c "
import yaml
with open('config/watcher_config.yaml', 'r') as f:
    config = yaml.safe_load(f)
    print(f'Config sections: {list(config.keys())}')
" && pass_test "watcher_config.yaml parsing" || fail_test "watcher_config.yaml parsing"
    else
        skip_test "watcher_config.yaml (file not found)"
    fi

    # Test PM2 config
    if [ -f "config/pm2.config.js" ]; then
        node -c "config/pm2.config.js" 2>/dev/null && \
            pass_test "pm2.config.js syntax" || fail_test "pm2.config.js syntax"
    else
        skip_test "pm2.config.js (file not found)"
    fi
}

test_daily_briefing() {
    log_info "Testing daily briefing generator..."

    cd "$PROJECT_ROOT"
    export DRY_RUN=true

    python -c "
from src.tasks.daily_briefing import DailyBriefingGenerator

generator = DailyBriefingGenerator(dry_run=True)

# Test briefing generation
briefing = generator.generate()
print(f'Briefing generated: {len(briefing)} characters')
print(f'Preview: {briefing[:200]}...')
" && pass_test "Daily briefing generator" || fail_test "Daily briefing generator"
}

test_integrity_hashing() {
    log_info "Testing integrity hashing..."

    cd "$PROJECT_ROOT"

    python -c "
from src.common.integrity import generate_hash, verify_hash
from datetime import datetime

action_type = 'email'
parameters = {'to': 'test@example.com', 'subject': 'Test'}
timestamp = datetime.utcnow().isoformat()

hash_value = generate_hash(action_type, parameters, timestamp)
print(f'Generated hash: {hash_value[:16]}...')

# Verify hash
is_valid = verify_hash(action_type, parameters, timestamp, hash_value)
print(f'Hash verification: {is_valid}')
assert is_valid, 'Hash verification failed'
" && pass_test "Integrity hashing" || fail_test "Integrity hashing"
}

# =============================================================================
# Main Test Runner
# =============================================================================

main() {
    echo ""
    echo "=============================================="
    echo "  AI Employee Silver Tier - E2E Test Suite"
    echo "=============================================="
    echo ""
    echo "Project root: $PROJECT_ROOT"
    echo "Dry-run mode: ENABLED"
    echo ""

    # Run all tests
    test_python_imports
    echo ""

    test_vault_operations
    echo ""

    test_idempotency_db
    echo ""

    test_audit_logger
    echo ""

    test_resource_monitor
    echo ""

    test_scheduler
    echo ""

    test_daily_briefing
    echo ""

    test_integrity_hashing
    echo ""

    test_whatsapp_webhook_syntax
    echo ""

    test_gmail_mcp_typescript
    echo ""

    test_linkedin_mcp_typescript
    echo ""

    test_config_files
    echo ""

    # Summary
    echo "=============================================="
    echo "                 Test Summary"
    echo "=============================================="
    echo ""
    echo -e "  ${GREEN}Passed:${NC}  $TESTS_PASSED"
    echo -e "  ${RED}Failed:${NC}  $TESTS_FAILED"
    echo -e "  ${YELLOW}Skipped:${NC} $TESTS_SKIPPED"
    echo ""

    TOTAL=$((TESTS_PASSED + TESTS_FAILED))
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}All $TOTAL tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}$TESTS_FAILED of $TOTAL tests failed.${NC}"
        exit 1
    fi
}

# Run main
main "$@"
