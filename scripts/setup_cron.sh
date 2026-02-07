#!/bin/bash
#
# Cron Setup Script for AI Employee Silver Tier (Mac/Linux)
#
# Registers scheduled tasks in the user's crontab:
# - Daily briefing at 8am
#
# Usage:
#   ./scripts/setup_cron.sh
#   ./scripts/setup_cron.sh --remove    # Remove scheduled tasks
#   ./scripts/setup_cron.sh --list      # List current crontab
#
# Implements T048 from tasks.md

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CRON_MARKER="# AI-EMPLOYEE-TASK"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if crontab is available
check_cron() {
    if ! command -v crontab &> /dev/null; then
        error "crontab command not found. Please install cron."
        exit 1
    fi
}

# Get the Python path
get_python() {
    if command -v python3 &> /dev/null; then
        echo "python3"
    elif command -v python &> /dev/null; then
        echo "python"
    else
        error "Python not found. Please install Python 3.10+."
        exit 1
    fi
}

# List current AI Employee cron jobs
list_jobs() {
    info "Current AI Employee scheduled tasks:"
    echo ""
    crontab -l 2>/dev/null | grep "$CRON_MARKER" || echo "No AI Employee tasks found."
    echo ""
}

# Remove all AI Employee cron jobs
remove_jobs() {
    info "Removing AI Employee scheduled tasks..."

    # Get current crontab, remove AI Employee entries
    crontab -l 2>/dev/null | grep -v "$CRON_MARKER" | crontab - 2>/dev/null || true

    info "Removed all AI Employee scheduled tasks."
}

# Add scheduled tasks
add_jobs() {
    local python_cmd=$(get_python)

    info "Adding AI Employee scheduled tasks..."
    info "Project root: $PROJECT_ROOT"
    info "Python: $python_cmd"

    # Get current crontab (create empty if none exists)
    local current_crontab
    current_crontab=$(crontab -l 2>/dev/null || echo "")

    # Remove existing AI Employee entries
    current_crontab=$(echo "$current_crontab" | grep -v "$CRON_MARKER" || true)

    # Define scheduled tasks
    local tasks=""

    # Daily briefing at 8am
    tasks+="0 8 * * * cd $PROJECT_ROOT && $python_cmd -m src.watchers.scheduler --task daily_briefing >> $PROJECT_ROOT/logs/scheduler.log 2>&1 $CRON_MARKER:daily_briefing"
    tasks+=$'\n'

    # Weekly cleanup at 2am on Sunday (optional)
    tasks+="0 2 * * 0 cd $PROJECT_ROOT && $python_cmd -c 'from src.common.idempotency import get_idempotency_db; db = get_idempotency_db(); db.cleanup_expired()' >> $PROJECT_ROOT/logs/cleanup.log 2>&1 $CRON_MARKER:weekly_cleanup"

    # Combine and install
    local new_crontab="$current_crontab"
    if [ -n "$current_crontab" ]; then
        new_crontab+=$'\n'
    fi
    new_crontab+="$tasks"

    echo "$new_crontab" | crontab -

    info "Scheduled tasks added successfully!"
    echo ""
    info "Added tasks:"
    echo "  - Daily briefing: 8:00 AM every day"
    echo "  - Weekly cleanup: 2:00 AM every Sunday"
    echo ""
    info "To view tasks: ./scripts/setup_cron.sh --list"
    info "To remove tasks: ./scripts/setup_cron.sh --remove"
}

# Ensure logs directory exists
ensure_logs_dir() {
    mkdir -p "$PROJECT_ROOT/logs"
}

# Main
main() {
    check_cron
    ensure_logs_dir

    case "${1:-}" in
        --list|-l)
            list_jobs
            ;;
        --remove|-r)
            remove_jobs
            ;;
        --help|-h)
            echo "Usage: $0 [--list|--remove|--help]"
            echo ""
            echo "Options:"
            echo "  --list, -l    List current AI Employee scheduled tasks"
            echo "  --remove, -r  Remove all AI Employee scheduled tasks"
            echo "  --help, -h    Show this help message"
            echo ""
            echo "Without options, adds/updates scheduled tasks."
            ;;
        *)
            add_jobs
            ;;
    esac
}

main "$@"
