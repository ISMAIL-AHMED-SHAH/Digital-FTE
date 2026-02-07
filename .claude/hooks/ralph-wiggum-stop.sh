#!/bin/bash
# Ralph Wiggum Stop Hook - Hybrid Completion Detection (FR-019-020)
#
# This hook is called by Claude Code after each autonomous action.
# It implements hybrid completion detection:
# 1. Semantic detection: Analyzes Claude's response for completion phrases
# 2. Task-based detection: Checks if the task list shows all tasks complete
# 3. Checkpoint detection: Looks for explicit approval request markers
#
# Exit codes:
#   0 = Continue (no stop signal)
#   1 = Stop (completion detected or approval needed)
#
# Environment variables expected:
#   CLAUDE_RESPONSE - The text of Claude's last response
#   TASK_FILE - Path to the current tasks.md file (optional)
#   APPROVAL_DIR - Path to the approval requests directory

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/../.."
LOG_FILE="${PROJECT_ROOT}/logs/ralph-wiggum-stop.log"
APPROVAL_DIR="${APPROVAL_DIR:-${PROJECT_ROOT}/data/approvals}"

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date -Iseconds)] $*" >> "$LOG_FILE"
}

# =============================================================================
# SEMANTIC COMPLETION DETECTION
# =============================================================================
# Detects completion phrases in Claude's response

COMPLETION_PHRASES=(
    "all tasks.*complet"
    "implementation.*complete"
    "phase.*complete"
    "finished.*all"
    "work.*complete"
    "done.*with.*tasks"
    "completed.*successfully"
    "all.*items.*done"
    "no.*remaining.*tasks"
    "nothing.*left.*to.*do"
)

check_semantic_completion() {
    local response="${CLAUDE_RESPONSE:-}"

    if [[ -z "$response" ]]; then
        return 1  # No response to analyze
    fi

    # Convert to lowercase for matching
    local lower_response
    lower_response=$(echo "$response" | tr '[:upper:]' '[:lower:]')

    for phrase in "${COMPLETION_PHRASES[@]}"; do
        if echo "$lower_response" | grep -qE "$phrase"; then
            log "Semantic completion detected: matched '$phrase'"
            return 0
        fi
    done

    return 1
}

# =============================================================================
# TASK-BASED COMPLETION DETECTION
# =============================================================================
# Checks if all tasks in tasks.md are marked complete

check_task_completion() {
    local task_file="${TASK_FILE:-}"

    # Try to find tasks.md if not specified
    if [[ -z "$task_file" ]]; then
        # Look for tasks.md in common locations
        for candidate in \
            "${PROJECT_ROOT}/specs/"*/tasks.md \
            "${PROJECT_ROOT}/tasks.md" \
            "${PROJECT_ROOT}/specs/tasks.md"
        do
            if [[ -f "$candidate" ]]; then
                task_file="$candidate"
                break
            fi
        done
    fi

    if [[ -z "$task_file" || ! -f "$task_file" ]]; then
        log "No tasks.md found for task-based detection"
        return 1
    fi

    # Count incomplete vs complete tasks
    # Assumes format: - [ ] incomplete or - [x] complete
    local incomplete
    local complete

    incomplete=$(grep -cE '^\s*-\s*\[\s*\]' "$task_file" 2>/dev/null || echo "0")
    complete=$(grep -cE '^\s*-\s*\[[xX]\]' "$task_file" 2>/dev/null || echo "0")

    log "Task status: $complete complete, $incomplete incomplete"

    if [[ "$incomplete" -eq 0 && "$complete" -gt 0 ]]; then
        log "Task-based completion detected: all $complete tasks complete"
        return 0
    fi

    return 1
}

# =============================================================================
# CHECKPOINT/APPROVAL DETECTION
# =============================================================================
# Detects when Claude is requesting human approval

APPROVAL_PHRASES=(
    "awaiting.*approval"
    "needs.*your.*approval"
    "please.*review.*and.*approve"
    "requires.*human.*review"
    "waiting.*for.*confirmation"
    "approval.*required"
    "human.*decision.*needed"
    "please.*confirm"
    "should.*I.*proceed"
    "do.*you.*want.*me.*to"
)

check_approval_request() {
    local response="${CLAUDE_RESPONSE:-}"

    if [[ -z "$response" ]]; then
        return 1
    fi

    local lower_response
    lower_response=$(echo "$response" | tr '[:upper:]' '[:lower:]')

    for phrase in "${APPROVAL_PHRASES[@]}"; do
        if echo "$lower_response" | grep -qE "$phrase"; then
            log "Approval request detected: matched '$phrase'"
            # Create approval request file
            create_approval_request "$response"
            return 0
        fi
    done

    return 1
}

create_approval_request() {
    local response="$1"
    local timestamp
    timestamp=$(date -Iseconds)
    local request_id
    request_id="approval-$(date +%Y%m%d-%H%M%S)-$$"

    mkdir -p "$APPROVAL_DIR"

    cat > "${APPROVAL_DIR}/${request_id}.json" << EOF
{
    "id": "${request_id}",
    "created_at": "${timestamp}",
    "status": "pending",
    "type": "ralph_wiggum_checkpoint",
    "context": {
        "response_excerpt": $(echo "$response" | head -c 500 | jq -Rs .)
    },
    "actions": ["approve", "reject", "modify"]
}
EOF

    log "Created approval request: ${request_id}"
}

# =============================================================================
# ERROR STATE DETECTION
# =============================================================================
# Detects if Claude is in an error state that requires human intervention

ERROR_PHRASES=(
    "error.*cannot.*proceed"
    "failed.*after.*retries"
    "authentication.*failed"
    "permission.*denied"
    "unable.*to.*continue"
    "critical.*error"
    "unrecoverable.*error"
    "requires.*manual.*intervention"
)

check_error_state() {
    local response="${CLAUDE_RESPONSE:-}"

    if [[ -z "$response" ]]; then
        return 1
    fi

    local lower_response
    lower_response=$(echo "$response" | tr '[:upper:]' '[:lower:]')

    for phrase in "${ERROR_PHRASES[@]}"; do
        if echo "$lower_response" | grep -qE "$phrase"; then
            log "Error state detected: matched '$phrase'"
            return 0
        fi
    done

    return 1
}

# =============================================================================
# ITERATION LIMIT CHECK
# =============================================================================
# Prevents infinite loops by tracking iteration count

MAX_ITERATIONS="${RALPH_WIGGUM_MAX_ITERATIONS:-50}"
ITERATION_FILE="${PROJECT_ROOT}/.ralph-wiggum-iterations"

check_iteration_limit() {
    local current=0

    if [[ -f "$ITERATION_FILE" ]]; then
        current=$(cat "$ITERATION_FILE" 2>/dev/null || echo "0")
    fi

    current=$((current + 1))
    echo "$current" > "$ITERATION_FILE"

    if [[ "$current" -ge "$MAX_ITERATIONS" ]]; then
        log "Iteration limit reached: $current >= $MAX_ITERATIONS"
        # Reset counter for next run
        echo "0" > "$ITERATION_FILE"
        return 0
    fi

    log "Iteration $current of $MAX_ITERATIONS"
    return 1
}

reset_iteration_counter() {
    echo "0" > "$ITERATION_FILE"
    log "Iteration counter reset"
}

# =============================================================================
# PROMISE-BASED COMPLETION DETECTION (T064 - FR-020)
# =============================================================================
# Checks for explicit completion signal in promise file

PROMISE_FILE="${RALPH_WIGGUM_PROMISE_FILE:-${PROJECT_ROOT}/vault/.ralph_completion_promise.json}"
VAULT_PATH="${VAULT_PATH:-${PROJECT_ROOT}/vault}"

check_promise_completion() {
    if [[ ! -f "$PROMISE_FILE" ]]; then
        return 1
    fi

    # Parse JSON for completed flag
    if command -v jq &> /dev/null; then
        local completed
        completed=$(jq -r '.completed // false' "$PROMISE_FILE" 2>/dev/null || echo "false")
        local stop_signal
        stop_signal=$(jq -r '.stop // false' "$PROMISE_FILE" 2>/dev/null || echo "false")
        local message
        message=$(jq -r '.message // "Promise fulfilled"' "$PROMISE_FILE" 2>/dev/null || echo "Promise fulfilled")

        if [[ "$completed" == "true" ]] || [[ "$stop_signal" == "true" ]]; then
            log "Promise completion detected: $message"
            # Clean up promise file
            rm -f "$PROMISE_FILE"
            return 0
        fi
    else
        # Fallback: grep for completed: true
        if grep -q '"completed":\s*true' "$PROMISE_FILE" 2>/dev/null; then
            log "Promise completion detected (grep fallback)"
            rm -f "$PROMISE_FILE"
            return 0
        fi
    fi

    return 1
}

# =============================================================================
# FILE-BASED COMPLETION DETECTION (T064 - FR-019)
# =============================================================================
# Checks if task file has been moved to Done folder

check_file_completion() {
    local task_id="${RALPH_WIGGUM_TASK_ID:-}"

    # Check if Needs_Action is empty
    local needs_action="${VAULT_PATH}/Needs_Action"
    if [[ -d "$needs_action" ]]; then
        local pending_count
        pending_count=$(find "$needs_action" -name "*.md" 2>/dev/null | wc -l)
        if [[ "$pending_count" -eq 0 ]]; then
            log "File-based completion: Needs_Action folder is empty"
            return 0
        fi
    fi

    # Check if specific task moved to Done
    if [[ -n "$task_id" ]]; then
        local done_folder="${VAULT_PATH}/Done"
        if [[ -d "$done_folder" ]]; then
            if find "$done_folder" -name "*${task_id}*" 2>/dev/null | grep -q .; then
                log "File-based completion: Task $task_id found in Done folder"
                return 0
            fi
        fi
    fi

    return 1
}

# =============================================================================
# APPROVAL PENDING CHECK
# =============================================================================
# Checks if there are pending HITL approvals

check_pending_approvals() {
    local needs_action="${VAULT_PATH}/Needs_Action"

    if [[ ! -d "$needs_action" ]]; then
        return 1
    fi

    # Look for approval request files
    for file in "$needs_action"/*approval*.md "$needs_action"/*-post-*.md; do
        if [[ -f "$file" ]]; then
            # Check if it's actually an approval request
            if grep -qi "approval required\|waiting for approval\|type: approval" "$file" 2>/dev/null; then
                log "HITL approval pending: $(basename "$file")"
                return 0
            fi
        fi
    done

    return 1
}

# =============================================================================
# MAIN EXECUTION
# =============================================================================

main() {
    log "=== Ralph Wiggum Stop Hook Invoked ==="

    # Check each detection method
    local should_stop=false
    local stop_reason=""

    # 1. Check iteration limit first (safety)
    if check_iteration_limit; then
        should_stop=true
        stop_reason="iteration_limit"
    fi

    # 2. Check promise-based completion (highest priority for explicit signals)
    if ! $should_stop && check_promise_completion; then
        should_stop=true
        stop_reason="promise_completion"
        reset_iteration_counter
    fi

    # 3. Check file-based completion
    if ! $should_stop && check_file_completion; then
        should_stop=true
        stop_reason="file_completion"
        reset_iteration_counter
    fi

    # 4. Check for error states
    if ! $should_stop && check_error_state; then
        should_stop=true
        stop_reason="error_state"
    fi

    # 5. Check for pending HITL approvals
    if ! $should_stop && check_pending_approvals; then
        should_stop=true
        stop_reason="approval_pending"
    fi

    # 6. Check for approval requests in response
    if ! $should_stop && check_approval_request; then
        should_stop=true
        stop_reason="approval_required"
    fi

    # 7. Check semantic completion
    if ! $should_stop && check_semantic_completion; then
        should_stop=true
        stop_reason="semantic_completion"
        reset_iteration_counter
    fi

    # 8. Check task-based completion
    if ! $should_stop && check_task_completion; then
        should_stop=true
        stop_reason="task_completion"
        reset_iteration_counter
    fi

    # Output result
    if $should_stop; then
        log "STOP signal: $stop_reason"
        echo "{\"stop\": true, \"reason\": \"$stop_reason\"}"
        exit 1
    else
        log "CONTINUE signal"
        echo "{\"stop\": false}"
        exit 0
    fi
}

# Run main function
main "$@"
