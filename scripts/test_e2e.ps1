# =============================================================================
# End-to-End Test Script for AI Employee Silver Tier (Windows PowerShell)
# =============================================================================
#
# This script tests the complete system flow in dry-run mode:
# 1. Python module imports
# 2. Vault operations
# 3. Idempotency database
# 4. Resource monitor
# 5. TypeScript compilation
#
# Usage:
#   .\scripts\test_e2e.ps1 [-Verbose]
#
# Environment:
#   DRY_RUN=true is automatically set for all tests
#
# =============================================================================

param(
    [switch]$VerboseOutput
)

$ErrorActionPreference = "Continue"

# Colors
$Green = "Green"
$Red = "Red"
$Yellow = "Yellow"
$Blue = "Cyan"

# Configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

# Test counters
$script:TestsPassed = 0
$script:TestsFailed = 0
$script:TestsSkipped = 0

# Logging functions
function Write-Info { param($Message) Write-Host "[INFO] $Message" -ForegroundColor $Blue }
function Write-Pass { param($Message) Write-Host "[PASS] $Message" -ForegroundColor $Green; $script:TestsPassed++ }
function Write-Fail { param($Message) Write-Host "[FAIL] $Message" -ForegroundColor $Red; $script:TestsFailed++ }
function Write-Skip { param($Message) Write-Host "[SKIP] $Message" -ForegroundColor $Yellow; $script:TestsSkipped++ }
function Write-Debug { param($Message) if ($VerboseOutput) { Write-Host "[DEBUG] $Message" -ForegroundColor $Blue } }

# =============================================================================
# Test Functions
# =============================================================================

function Test-PythonImports {
    Write-Info "Testing Python module imports..."

    Set-Location $ProjectRoot
    $env:DRY_RUN = "true"
    $env:PYTHONPATH = $ProjectRoot

    $modules = @(
        "src.common.vault",
        "src.common.audit_logger",
        "src.common.idempotency",
        "src.common.integrity",
        "src.watchers.base_watcher",
        "src.watchers.resource_monitor",
        "src.watchers.scheduler",
        "src.tasks.daily_briefing"
    )

    foreach ($module in $modules) {
        $result = python -c "import $module" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Pass "Import: $module"
        } else {
            Write-Fail "Import: $module"
            Write-Debug $result
        }
    }
}

function Test-VaultOperations {
    Write-Info "Testing vault operations..."

    Set-Location $ProjectRoot
    $env:DRY_RUN = "true"
    $env:PYTHONPATH = $ProjectRoot

    $code = @"
from src.common.vault import get_vault
vault = get_vault()
print(f'Vault path: {vault.vault_path}')
print(f'Folders: {list(vault.folders.keys())}')
"@

    $result = python -c $code 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Pass "Vault initialization"
        Write-Debug $result
    } else {
        Write-Fail "Vault initialization"
        Write-Debug $result
    }
}

function Test-IdempotencyDB {
    Write-Info "Testing idempotency database..."

    Set-Location $ProjectRoot
    $env:DRY_RUN = "true"
    $env:PYTHONPATH = $ProjectRoot

    $code = @"
from src.common.idempotency import get_idempotency_db
db = get_idempotency_db()
is_processed = db.is_processed('test-message-123', 'test')
print(f'Test message processed: {is_processed}')
stats = db.get_stats()
print(f'DB stats: {stats}')
"@

    $result = python -c $code 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Pass "Idempotency database"
        Write-Debug $result
    } else {
        Write-Fail "Idempotency database"
        Write-Debug $result
    }
}

function Test-ResourceMonitor {
    Write-Info "Testing resource monitor..."

    Set-Location $ProjectRoot
    $env:DRY_RUN = "true"
    $env:PYTHONPATH = $ProjectRoot

    $code = @"
from src.watchers.resource_monitor import ResourceMonitor
monitor = ResourceMonitor(dry_run=True)
usage = monitor.total_memory_usage()
print(f'Memory usage: {usage}')
stats = monitor.get_stats()
print(f'Stats: {stats}')
"@

    $result = python -c $code 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Pass "Resource monitor"
        Write-Debug $result
    } else {
        Write-Fail "Resource monitor"
        Write-Debug $result
    }
}

function Test-Scheduler {
    Write-Info "Testing scheduler..."

    Set-Location $ProjectRoot
    $env:DRY_RUN = "true"
    $env:PYTHONPATH = $ProjectRoot

    $code = @"
from src.watchers.scheduler import TaskScheduler
scheduler = TaskScheduler(dry_run=True)
tasks = scheduler.list_tasks()
print(f'Tasks: {[t.name for t in tasks]}')
"@

    $result = python -c $code 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Pass "Scheduler"
        Write-Debug $result
    } else {
        Write-Fail "Scheduler"
        Write-Debug $result
    }
}

function Test-DailyBriefing {
    Write-Info "Testing daily briefing generator..."

    Set-Location $ProjectRoot
    $env:DRY_RUN = "true"
    $env:PYTHONPATH = $ProjectRoot

    $code = @"
from src.tasks.daily_briefing import DailyBriefingGenerator
generator = DailyBriefingGenerator(dry_run=True)
briefing = generator.generate_briefing()
print(f'Briefing length: {len(briefing)} chars')
"@

    $result = python -c $code 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Pass "Daily briefing generator"
        Write-Debug $result
    } else {
        Write-Fail "Daily briefing generator"
        Write-Debug $result
    }
}

function Test-IntegrityHashing {
    Write-Info "Testing integrity hashing..."

    Set-Location $ProjectRoot
    $env:PYTHONPATH = $ProjectRoot

    $code = @"
from src.common.integrity import generate_hash, verify_hash
from datetime import datetime
action_type = 'email'
parameters = {'to': 'test@example.com', 'subject': 'Test'}
timestamp = datetime.utcnow().isoformat()
hash_value = generate_hash(action_type, parameters, timestamp)
is_valid = verify_hash(action_type, parameters, timestamp, hash_value)
print(f'Hash valid: {is_valid}')
assert is_valid
"@

    $result = python -c $code 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Pass "Integrity hashing"
    } else {
        Write-Fail "Integrity hashing"
        Write-Debug $result
    }
}

function Test-WhatsAppWebhookSyntax {
    Write-Info "Testing WhatsApp webhook syntax..."

    Set-Location $ProjectRoot
    $env:PYTHONPATH = $ProjectRoot

    $code = @"
import ast
with open('src/watchers/whatsapp_webhook.py', 'r') as f:
    ast.parse(f.read())
print('Syntax valid')
"@

    $result = python -c $code 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Pass "WhatsApp webhook syntax"
    } else {
        Write-Fail "WhatsApp webhook syntax"
        Write-Debug $result
    }
}

function Test-GmailMCPTypeScript {
    Write-Info "Testing Gmail MCP TypeScript..."

    $gmailPath = Join-Path $ProjectRoot "src\mcp_servers\gmail"

    if (Test-Path $gmailPath) {
        Set-Location $gmailPath

        if (Get-Command npx -ErrorAction SilentlyContinue) {
            $result = npx tsc --noEmit 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Pass "Gmail MCP TypeScript compilation"
            } else {
                Write-Fail "Gmail MCP TypeScript compilation"
                Write-Debug $result
            }
        } else {
            Write-Skip "Gmail MCP TypeScript (npx not available)"
        }
    } else {
        Write-Skip "Gmail MCP TypeScript (directory not found)"
    }
}

function Test-LinkedInMCPTypeScript {
    Write-Info "Testing LinkedIn MCP TypeScript..."

    $linkedinPath = Join-Path $ProjectRoot "src\mcp_servers\linkedin"

    if (Test-Path $linkedinPath) {
        Set-Location $linkedinPath

        $nodeModules = Join-Path $linkedinPath "node_modules"
        if (Test-Path $nodeModules) {
            if (Get-Command npx -ErrorAction SilentlyContinue) {
                $result = npx tsc --noEmit 2>&1
                if ($LASTEXITCODE -eq 0) {
                    Write-Pass "LinkedIn MCP TypeScript compilation"
                } else {
                    Write-Fail "LinkedIn MCP TypeScript compilation"
                    Write-Debug $result
                }
            } else {
                Write-Skip "LinkedIn MCP TypeScript (npx not available)"
            }
        } else {
            Write-Skip "LinkedIn MCP TypeScript (node_modules not installed)"
        }
    } else {
        Write-Skip "LinkedIn MCP TypeScript (directory not found)"
    }
}

function Test-ConfigFiles {
    Write-Info "Testing configuration files..."

    Set-Location $ProjectRoot
    $env:PYTHONPATH = $ProjectRoot

    # Test YAML config
    $configPath = Join-Path $ProjectRoot "config\watcher_config.yaml"
    if (Test-Path $configPath) {
        $code = @"
import yaml
with open('config/watcher_config.yaml', 'r') as f:
    config = yaml.safe_load(f)
    print(f'Sections: {list(config.keys())}')
"@
        $result = python -c $code 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Pass "watcher_config.yaml parsing"
        } else {
            Write-Fail "watcher_config.yaml parsing"
        }
    } else {
        Write-Skip "watcher_config.yaml (not found)"
    }

    # Test PM2 config
    $pm2Path = Join-Path $ProjectRoot "config\pm2.config.js"
    if (Test-Path $pm2Path) {
        if (Get-Command node -ErrorAction SilentlyContinue) {
            $result = node --check $pm2Path 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Pass "pm2.config.js syntax"
            } else {
                Write-Fail "pm2.config.js syntax"
            }
        } else {
            Write-Skip "pm2.config.js (node not available)"
        }
    } else {
        Write-Skip "pm2.config.js (not found)"
    }
}

# =============================================================================
# Main Test Runner
# =============================================================================

function Main {
    Write-Host ""
    Write-Host "=============================================="
    Write-Host "  AI Employee Silver Tier - E2E Test Suite"
    Write-Host "=============================================="
    Write-Host ""
    Write-Host "Project root: $ProjectRoot"
    Write-Host "Dry-run mode: ENABLED"
    Write-Host ""

    # Run all tests
    Test-PythonImports
    Write-Host ""

    Test-VaultOperations
    Write-Host ""

    Test-IdempotencyDB
    Write-Host ""

    Test-ResourceMonitor
    Write-Host ""

    Test-Scheduler
    Write-Host ""

    Test-DailyBriefing
    Write-Host ""

    Test-IntegrityHashing
    Write-Host ""

    Test-WhatsAppWebhookSyntax
    Write-Host ""

    Test-GmailMCPTypeScript
    Write-Host ""

    Test-LinkedInMCPTypeScript
    Write-Host ""

    Test-ConfigFiles
    Write-Host ""

    # Summary
    Write-Host "=============================================="
    Write-Host "                 Test Summary"
    Write-Host "=============================================="
    Write-Host ""
    Write-Host "  Passed:  $script:TestsPassed" -ForegroundColor $Green
    Write-Host "  Failed:  $script:TestsFailed" -ForegroundColor $Red
    Write-Host "  Skipped: $script:TestsSkipped" -ForegroundColor $Yellow
    Write-Host ""

    $Total = $script:TestsPassed + $script:TestsFailed
    if ($script:TestsFailed -eq 0) {
        Write-Host "All $Total tests passed!" -ForegroundColor $Green
        exit 0
    } else {
        Write-Host "$script:TestsFailed of $Total tests failed." -ForegroundColor $Red
        exit 1
    }
}

# Run main
Main
