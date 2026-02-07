#Requires -Version 5.1
<#
.SYNOPSIS
    Windows Task Scheduler Setup for AI Employee Silver Tier

.DESCRIPTION
    Registers scheduled tasks in Windows Task Scheduler:
    - Daily briefing at 8am

.PARAMETER Remove
    Remove all AI Employee scheduled tasks

.PARAMETER List
    List current AI Employee scheduled tasks

.EXAMPLE
    .\scripts\setup_scheduler.ps1
    Adds scheduled tasks

.EXAMPLE
    .\scripts\setup_scheduler.ps1 -List
    Lists current tasks

.EXAMPLE
    .\scripts\setup_scheduler.ps1 -Remove
    Removes all AI Employee tasks

.NOTES
    Implements T049 from tasks.md
#>

[CmdletBinding()]
param(
    [switch]$Remove,
    [switch]$List,
    [switch]$Help
)

# Configuration
$TaskPrefix = "AIEmployee"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not $ProjectRoot) {
    $ProjectRoot = (Get-Location).Path
}

# Colors
function Write-Success($Message) {
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Info($Message) {
    Write-Host "[INFO] $Message" -ForegroundColor Cyan
}

function Write-Warn($Message) {
    Write-Host "[WARN] $Message" -ForegroundColor Yellow
}

function Write-Err($Message) {
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Find Python
function Get-PythonPath {
    $pythonPaths = @(
        "python",
        "python3",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
        "C:\Python312\python.exe",
        "C:\Python311\python.exe",
        "C:\Python310\python.exe"
    )

    foreach ($path in $pythonPaths) {
        try {
            $result = & $path --version 2>&1
            if ($LASTEXITCODE -eq 0) {
                return $path
            }
        } catch {
            continue
        }
    }

    Write-Err "Python not found. Please install Python 3.10+."
    exit 1
}

# List AI Employee tasks
function Get-AIEmployeeTasks {
    Write-Info "Current AI Employee scheduled tasks:"
    Write-Host ""

    $tasks = Get-ScheduledTask -TaskName "$TaskPrefix*" -ErrorAction SilentlyContinue

    if ($tasks) {
        foreach ($task in $tasks) {
            $info = Get-ScheduledTaskInfo -TaskName $task.TaskName -ErrorAction SilentlyContinue
            Write-Host "  $($task.TaskName)"
            Write-Host "    State: $($task.State)"
            Write-Host "    Last Run: $($info.LastRunTime)"
            Write-Host "    Next Run: $($info.NextRunTime)"
            Write-Host ""
        }
    } else {
        Write-Host "  No AI Employee tasks found."
    }
}

# Remove AI Employee tasks
function Remove-AIEmployeeTasks {
    Write-Info "Removing AI Employee scheduled tasks..."

    $tasks = Get-ScheduledTask -TaskName "$TaskPrefix*" -ErrorAction SilentlyContinue

    if ($tasks) {
        foreach ($task in $tasks) {
            Write-Info "Removing: $($task.TaskName)"
            Unregister-ScheduledTask -TaskName $task.TaskName -Confirm:$false
        }
        Write-Success "Removed all AI Employee scheduled tasks."
    } else {
        Write-Info "No AI Employee tasks to remove."
    }
}

# Create scheduled tasks
function Add-AIEmployeeTasks {
    $pythonPath = Get-PythonPath

    Write-Info "Adding AI Employee scheduled tasks..."
    Write-Info "Project root: $ProjectRoot"
    Write-Info "Python: $pythonPath"

    # Ensure logs directory exists
    $logsDir = Join-Path $ProjectRoot "logs"
    if (-not (Test-Path $logsDir)) {
        New-Item -ItemType Directory -Path $logsDir -Force | Out-Null
    }

    # Task 1: Daily Briefing at 8am
    $taskName = "${TaskPrefix}_DailyBriefing"
    $action = New-ScheduledTaskAction `
        -Execute $pythonPath `
        -Argument "-m src.watchers.scheduler --task daily_briefing" `
        -WorkingDirectory $ProjectRoot

    $trigger = New-ScheduledTaskTrigger -Daily -At 8:00AM

    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RunOnlyIfNetworkAvailable:$false `
        -WakeToRun:$false

    $principal = New-ScheduledTaskPrincipal `
        -UserId $env:USERNAME `
        -LogonType Interactive `
        -RunLevel Limited

    # Remove existing task if present
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Description "AI Employee Daily Briefing - Generates summary document at 8am" `
        | Out-Null

    Write-Success "Created task: $taskName (8:00 AM daily)"

    # Task 2: Weekly Cleanup at 2am on Sunday
    $taskName = "${TaskPrefix}_WeeklyCleanup"
    $action = New-ScheduledTaskAction `
        -Execute $pythonPath `
        -Argument "-c `"from src.common.idempotency import get_idempotency_db; db = get_idempotency_db(); db.cleanup_expired()`"" `
        -WorkingDirectory $ProjectRoot

    $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 2:00AM

    # Remove existing task if present
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Description "AI Employee Weekly Cleanup - Removes expired idempotency records" `
        | Out-Null

    Write-Success "Created task: $taskName (2:00 AM every Sunday)"

    Write-Host ""
    Write-Success "Scheduled tasks added successfully!"
    Write-Host ""
    Write-Info "To view tasks: .\scripts\setup_scheduler.ps1 -List"
    Write-Info "To remove tasks: .\scripts\setup_scheduler.ps1 -Remove"
    Write-Info "Or use Task Scheduler GUI: taskschd.msc"
}

# Show help
function Show-Help {
    Write-Host @"
AI Employee Scheduler Setup Script

Usage:
    .\scripts\setup_scheduler.ps1 [options]

Options:
    -List       List current AI Employee scheduled tasks
    -Remove     Remove all AI Employee scheduled tasks
    -Help       Show this help message

Without options, adds/updates scheduled tasks.

Tasks Created:
    - Daily Briefing (8:00 AM daily)
    - Weekly Cleanup (2:00 AM every Sunday)
"@
}

# Main
if ($Help) {
    Show-Help
} elseif ($List) {
    Get-AIEmployeeTasks
} elseif ($Remove) {
    Remove-AIEmployeeTasks
} else {
    Add-AIEmployeeTasks
}
