# Tasks: Gold Tier - Autonomous Employee

**Input**: Design documents from `/specs/003-gold-tier-autonomous/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/

**Tests**: Tests are included per spec requirements for critical paths (FR-039 mandates comprehensive testing).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Based on plan.md structure:
- **Python code**: `src/` at repository root
- **Node.js MCP servers**: `src/mcp_servers/`
- **Tests**: `tests/unit/`, `tests/integration/`, `tests/fixtures/`
- **Skills**: `.claude/skills/`
- **Hooks**: `.claude/hooks/`
- **Config**: `config/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, configuration, and shared dependencies for Gold Tier

- [x] T001 Create Gold Tier directory structure per plan.md in src/tasks/, src/mcp_servers/odoo/, src/mcp_servers/facebook/, src/mcp_servers/instagram/, src/mcp_servers/twitter/
- [x] T002 [P] Create config/gold_tier.yaml with briefing schedule, rate limits, and Ralph Wiggum settings
- [x] T003 [P] Update config/.env.example with Odoo, Meta, and Twitter credential placeholders
- [x] T004 [P] Create scripts/init_gold_tier.sql with SQLite schema extensions for Gold Tier entities
- [x] T005 Initialize Node.js workspace for MCP servers with shared package.json in src/mcp_servers/
- [x] T006 [P] Create tests/fixtures/mock_odoo_api.py with mock Odoo JSON-RPC responses
- [x] T007 [P] Create tests/fixtures/mock_meta_api.py with mock Meta Graph API responses
- [x] T008 [P] Create tests/fixtures/mock_twitter_api.py with mock Twitter API v2 responses
- [x] T009 [P] Create tests/fixtures/sample_briefing_data.py with sample CEO Briefing test data

**Checkpoint**: ✅ Setup complete - all directories, configs, and fixtures in place (2026-02-05)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T010 Extend src/common/audit_logger.py with 90-day retention, compression at 30 days, and size alerting (FR-031-036)
- [x] T011 [P] Extend src/orchestrator/action_queue.py with graceful degradation queue for unavailable services (FR-028-029)
- [x] T012 [P] Create src/common/error_categorizer.py implementing error classification (Transient, Auth, Logic, Data, System) per FR-025
- [x] T013 Create src/common/retry_handler.py with exponential backoff (1s initial, 60s max, 5 retries) per FR-026
- [x] T014 Create .claude/hooks/ralph-wiggum-stop.sh implementing Stop hook with hybrid completion detection (FR-019-020)
- [x] T015 [P] Create .claude/plugins/ralph-wiggum/manifest.json with plugin metadata
- [x] T016 [P] Create .claude/plugins/ralph-wiggum/hooks/hooks.json with Stop hook registration
- [x] T017 Update .claude/settings.local.json with Gold Tier MCP server registrations and hook configuration

**Checkpoint**: ✅ Foundation ready - user story implementation can now begin (2026-02-06)

---

## Phase 3: User Story 1 - Odoo Accounting Integration (Priority: P1) 🎯 MVP

**Goal**: Enable AI Employee to manage accounting in Odoo - create draft invoices, payments, and retrieve financial summaries

**Independent Test**: Create customer invoice in vault → Odoo MCP drafts invoice → Human approval → Post to Odoo → Verify in Odoo UI

### Tests for User Story 1

- [x] T018 [P] [US1] Create tests/unit/test_odoo_client.py with connection, invoice, payment, and query tests
- [x] T019 [P] [US1] Create tests/integration/test_odoo_mcp.py with end-to-end MCP tool tests

### Implementation for User Story 1

- [x] T020 [P] [US1] Create src/mcp_servers/odoo/package.json with @modelcontextprotocol/sdk and axios dependencies
- [x] T021 [P] [US1] Create src/mcp_servers/odoo/lib/odoo_client.ts implementing JSON-RPC client with 30s timeout and connection pooling
- [x] T022 [US1] Create src/mcp_servers/odoo/tools/create_invoice.ts implementing create_invoice tool per contracts/odoo-mcp.json
- [x] T023 [US1] Create src/mcp_servers/odoo/tools/create_payment.ts implementing create_payment tool per contracts/odoo-mcp.json
- [x] T024 [US1] Create src/mcp_servers/odoo/tools/get_financial_summary.ts implementing get_financial_summary tool per contracts/odoo-mcp.json
- [x] T025 [US1] Create src/mcp_servers/odoo/index.ts as MCP server entry point registering all Odoo tools
- [x] T026 [US1] Create scripts/setup_odoo_connection.py for Odoo connectivity test and API key setup
- [x] T027 [US1] Create .claude/skills/odoo-ops/SKILL.md documenting Odoo accounting skill
- [x] T028 [US1] Create .claude/skills/odoo-ops/scripts/main_operation.py implementing Odoo skill entry point
- [x] T029 [US1] Add Odoo MCP server to ecosystem.config.js for PM2 management

**Checkpoint**: ✅ Odoo integration complete - can create invoices/payments and retrieve financials (2026-02-06)

---

## Phase 4: User Story 2 - Weekly Business Audit and CEO Briefing (Priority: P1)

**Goal**: Automatically audit business weekly and generate Monday Morning CEO Briefing with revenue, tasks, bottlenecks, and suggestions

**Independent Test**: Configure schedule → Run audit manually → Verify briefing contains accurate revenue, tasks, bottlenecks, suggestions

### Tests for User Story 2

- [x] T030 [P] [US2] Create tests/unit/test_ceo_briefing.py with briefing generation tests
- [x] T031 [P] [US2] Create tests/unit/test_subscription_audit.py with subscription analysis tests
- [x] T032 [P] [US2] Create tests/unit/test_bottleneck_detector.py with task duration analysis tests

### Implementation for User Story 2

- [x] T033 [P] [US2] Create src/tasks/__init__.py with Gold Tier task module initialization
- [x] T034 [US2] Create src/tasks/subscription_audit.py implementing subscription pattern analysis (FR-016)
- [x] T035 [US2] Create src/tasks/bottleneck_detector.py implementing task completion time analysis (FR-017)
- [x] T036 [US2] Create src/tasks/ceo_briefing.py implementing weekly audit and briefing generation (FR-013-015, FR-018)
- [x] T037 [US2] Create .claude/skills/ceo-briefing/SKILL.md documenting CEO Briefing skill
- [x] T038 [US2] Create .claude/skills/ceo-briefing/scripts/main_operation.py implementing briefing skill entry point
- [x] T039 [US2] Add scheduled task configuration for Sunday 11 PM audit in config/gold_tier.yaml

**Checkpoint**: ✅ CEO Briefing complete - weekly audit generates comprehensive business summary (2026-02-06)

---

## Phase 5: User Story 3 - Facebook and Instagram Integration (Priority: P2)

**Goal**: Post updates to Facebook Pages and Instagram Business accounts with HITL approval workflow

**Independent Test**: Create marketing content → Trigger draft post → Approve via HITL → Verify published on both platforms

### Tests for User Story 3

- [x] T040 [P] [US3] Create tests/integration/test_meta_mcps.py with Facebook and Instagram posting tests

### Implementation for User Story 3

- [x] T041 [P] [US3] Create src/mcp_servers/facebook/package.json with @modelcontextprotocol/sdk and axios dependencies
- [x] T042 [P] [US3] Create src/mcp_servers/instagram/package.json with @modelcontextprotocol/sdk and axios dependencies
- [x] T043 [US3] Create src/mcp_servers/facebook/lib/meta_oauth.ts with shared OAuth2 token refresh logic (FR-012a)
- [x] T044 [US3] Create src/mcp_servers/facebook/tools/create_post.ts implementing create_post tool per contracts/facebook-mcp.json
- [x] T045 [US3] Create src/mcp_servers/facebook/index.ts as Facebook MCP server entry point
- [x] T046 [US3] Create src/mcp_servers/instagram/tools/publish_media.ts implementing publish_media tool with two-step container workflow per contracts/instagram-mcp.json
- [x] T047 [US3] Create src/mcp_servers/instagram/index.ts as Instagram MCP server entry point
- [x] T048 [US3] Create scripts/setup_meta_oauth.py for Meta Business Suite OAuth setup
- [x] T049 [US3] Extend .claude/skills/social-ops/SKILL.md with Facebook and Instagram capabilities
- [x] T050 [US3] Extend .claude/skills/social-ops/scripts/main_operation.py with Facebook/Instagram posting
- [x] T051 [US3] Add Facebook and Instagram MCP servers to ecosystem.config.js

**Checkpoint**: ✅ Meta integration complete - can post to Facebook Pages and Instagram Business (2026-02-06)

---

## Phase 6: User Story 4 - Twitter/X Integration (Priority: P2)

**Goal**: Post tweets to Twitter/X with HITL approval, respecting 280-char limit and rate limits

**Independent Test**: Create tweet content → Trigger draft → Approve → Verify tweet published with correct text

### Tests for User Story 4

- [x] T052 [P] [US4] Create tests/integration/test_twitter_mcp.py with tweet posting and thread tests

### Implementation for User Story 4

- [x] T053 [P] [US4] Create src/mcp_servers/twitter/package.json with @modelcontextprotocol/sdk and twitter-api-v2 dependencies
- [x] T054 [US4] Create src/mcp_servers/twitter/lib/twitter_client.ts implementing OAuth 1.0a client wrapper
- [x] T055 [US4] Create src/mcp_servers/twitter/tools/post_tweet.ts implementing post_tweet tool per contracts/twitter-mcp.json
- [x] T056 [US4] Create src/mcp_servers/twitter/tools/validate_tweet.ts implementing character count validation
- [x] T057 [US4] Create src/mcp_servers/twitter/index.ts as Twitter MCP server entry point
- [x] T058 [US4] Create scripts/setup_twitter_oauth.py for Twitter API OAuth setup
- [x] T059 [US4] Extend .claude/skills/social-ops/SKILL.md with Twitter capabilities
- [x] T060 [US4] Extend .claude/skills/social-ops/scripts/main_operation.py with Twitter posting
- [x] T061 [US4] Add Twitter MCP server to ecosystem.config.js

**Checkpoint**: ✅ Twitter integration complete - can post tweets with character limit validation (2026-02-06)

---

## Phase 7: User Story 5 - Ralph Wiggum Autonomous Loop (Priority: P1)

**Goal**: Enable autonomous multi-step task completion using Stop hook pattern with file-based and promise-based completion detection

**Independent Test**: Start multi-step task → Loop continues through iterations → Completes when task file moves to /Done or promise emitted

### Tests for User Story 5

- [x] T062 [P] [US5] Create tests/integration/test_ralph_wiggum_loop.py with loop execution, completion, and max iteration tests

### Implementation for User Story 5

- [x] T063 [US5] Create src/tasks/ralph_loop_tracker.py implementing loop state tracking and iteration history (FR-023)
- [x] T064 [US5] Enhance .claude/hooks/ralph-wiggum-stop.sh with promise-based completion detection (FR-020)
- [x] T065 [US5] Create src/tasks/ralph_completion_checker.py implementing hybrid completion strategy (file + promise)
- [x] T066 [US5] Create src/tasks/ralph_summary_generator.py implementing completion summary generation (FR-024)
- [x] T067 [US5] Create .claude/skills/ralph-loop/SKILL.md documenting Ralph Wiggum loop skill
- [x] T068 [US5] Create .claude/skills/ralph-loop/scripts/main_operation.py implementing loop skill entry point
- [x] T069 [US5] Add max_iterations and timeout configuration to config/gold_tier.yaml (FR-022)

**Checkpoint**: ✅ Ralph Wiggum loop complete - autonomous multi-step tasks execute to completion (2026-02-07)

---

## Phase 8: User Story 6 - Error Recovery and Graceful Degradation (Priority: P2)

**Goal**: Handle errors gracefully with retry, degradation, watchdog restart, and quarantine

**Independent Test**: Simulate API failures → Observe retry with backoff → Verify graceful degradation activates → Confirm recovery on service restore

### Tests for User Story 6

- [x] T070 [P] [US6] Create tests/unit/test_error_recovery.py with retry, categorization, and queue tests
- [x] T071 [P] [US6] Create tests/integration/test_watchdog.py with crash detection and restart tests

### Implementation for User Story 6

- [x] T072 [US6] Create src/orchestrator/watchdog.py implementing process monitoring and auto-restart (FR-027)
- [x] T073 [US6] Create src/common/quarantine_handler.py implementing /Quarantine folder management (FR-030)
- [x] T074 [US6] Integrate error_categorizer.py with all MCP servers for consistent error classification
- [x] T075 [US6] Integrate retry_handler.py with all MCP servers for exponential backoff
- [x] T076 [US6] Integrate action_queue.py with graceful degradation for Odoo and social MCPs
- [x] T077 [US6] Add watchdog to ecosystem.config.js and PM2 startup sequence
- [x] T078 [US6] Create alert templates in config/ for Odoo, OAuth, loop, and log size alerts

**Checkpoint**: ✅ Error recovery complete - system handles failures gracefully and recovers automatically (2026-02-07)

---

## Phase 9: User Story 7 - Comprehensive Audit Logging (Priority: P2)

**Goal**: Log all actions with required fields, 90-day retention, compression, and queryability

**Independent Test**: Trigger actions → Verify log entries with all fields → Query logs by date/type/target → Confirm 90-day retention works

### Tests for User Story 7

- [x] T079 [P] [US7] Create tests/unit/test_audit_logging.py with log creation, query, and retention tests

### Implementation for User Story 7

- [x] T080 [US7] Extend src/common/audit_logger.py with log query support (date range, action type, target, result) (FR-034)
- [x] T081 [US7] Create src/tasks/log_maintenance.py implementing 30-day compression and 90-day cleanup (FR-033, FR-035)
- [x] T082 [US7] Create src/tasks/log_size_monitor.py implementing 80% size threshold alerting (FR-036)
- [x] T083 [US7] Integrate audit logging with all Odoo MCP tools
- [x] T084 [US7] Integrate audit logging with all social media MCP tools
- [x] T085 [US7] Integrate audit logging with Ralph Wiggum loop iterations
- [x] T086 [US7] Add log maintenance scheduled task to config/gold_tier.yaml

**Checkpoint**: ✅ Audit logging complete - all actions logged, queryable, with proper retention (2026-02-07)

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, integration, and final validation

- [x] T087 [P] Create docs/gold-tier-architecture.md with system architecture diagram and component interactions
- [x] T088 [P] Create docs/gold-tier-troubleshooting.md with runbooks for common issues (from plan.md Section 5.3)
- [x] T089 [P] Create docs/gold-tier-lessons-learned.md documenting implementation insights (FR-038)
- [x] T090 Update CLAUDE.md with Gold Tier skill documentation and MCP server references
- [x] T091 Run quickstart.md validation - execute all setup steps and verify end-to-end
- [x] T092 [P] Security audit - verify no credentials in code, all secrets in credential manager
- [x] T093 Performance validation - verify Odoo <5s, social posts <5min from approval
- [x] T094 Create release checklist for Gold Tier deployment

**Checkpoint**: ✅ Gold Tier implementation complete - all 94 tasks done (2026-02-07)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-9)**: All depend on Foundational phase completion
  - User stories can proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2)
- **Polish (Phase 10)**: Depends on all user stories being complete

### User Story Dependencies

| Story | Priority | Depends On | Can Start After |
|-------|----------|------------|-----------------|
| US1 - Odoo | P1 | Foundational | Phase 2 complete |
| US2 - CEO Briefing | P1 | US1 (for revenue data) | T025 (Odoo MCP) |
| US3 - Facebook/Instagram | P2 | Foundational | Phase 2 complete |
| US4 - Twitter | P2 | Foundational | Phase 2 complete |
| US5 - Ralph Wiggum | P1 | T014 (Stop hook) | Phase 2 complete |
| US6 - Error Recovery | P2 | T012-T013 (error handling) | Phase 2 complete |
| US7 - Audit Logging | P2 | T010 (audit_logger extension) | Phase 2 complete |

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- MCP library/client before tools
- Tools before MCP server entry point
- MCP server before skill
- Core implementation before PM2 integration

### Parallel Opportunities

**Phase 1 (all parallel)**:
- T002, T003, T004 can run in parallel
- T006, T007, T008, T009 can run in parallel

**Phase 2**:
- T011, T012 can run in parallel
- T015, T016 can run in parallel

**User Stories (after Phase 2)**:
- US1, US3, US4, US5, US6, US7 can all start in parallel (US2 waits for US1)
- Within each story, test tasks marked [P] can run in parallel
- Model/library tasks marked [P] can run in parallel

---

## Parallel Example: Phase 1 Setup

```bash
# Launch all fixture creation together:
Task: "Create tests/fixtures/mock_odoo_api.py"
Task: "Create tests/fixtures/mock_meta_api.py"
Task: "Create tests/fixtures/mock_twitter_api.py"
Task: "Create tests/fixtures/sample_briefing_data.py"

# Launch all config creation together:
Task: "Create config/gold_tier.yaml"
Task: "Update config/.env.example"
Task: "Create scripts/init_gold_tier.sql"
```

## Parallel Example: User Story 1 (Odoo)

```bash
# Launch tests together:
Task: "Create tests/unit/test_odoo_client.py"
Task: "Create tests/integration/test_odoo_mcp.py"

# Launch package.json and client together:
Task: "Create src/mcp_servers/odoo/package.json"
Task: "Create src/mcp_servers/odoo/lib/odoo_client.ts"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 5)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1 (Odoo)
4. Complete Phase 7: User Story 5 (Ralph Wiggum)
5. **STOP and VALIDATE**: Test Odoo integration and autonomous loop independently
6. This provides core Gold Tier value: accounting + autonomous execution

### Incremental Delivery

1. **MVP**: Setup + Foundational + US1 (Odoo) + US5 (Ralph Wiggum)
2. **+CEO Briefing**: Add US2 (requires US1 for revenue data)
3. **+Social Media**: Add US3 (Meta) + US4 (Twitter) in parallel
4. **+Reliability**: Add US6 (Error Recovery) + US7 (Audit Logging)
5. **+Polish**: Documentation and validation

### Parallel Team Strategy

With 3 developers after Foundational phase:
- Developer A: US1 (Odoo) → US2 (CEO Briefing)
- Developer B: US3 (Meta) → US4 (Twitter)
- Developer C: US5 (Ralph Wiggum) → US6 (Error Recovery) → US7 (Audit Logging)

---

## Summary

| Metric | Count |
|--------|-------|
| Total Tasks | 94 |
| Phase 1 (Setup) | 9 tasks |
| Phase 2 (Foundational) | 8 tasks |
| US1 (Odoo) | 12 tasks |
| US2 (CEO Briefing) | 10 tasks |
| US3 (Meta) | 12 tasks |
| US4 (Twitter) | 10 tasks |
| US5 (Ralph Wiggum) | 8 tasks |
| US6 (Error Recovery) | 9 tasks |
| US7 (Audit Logging) | 8 tasks |
| Phase 10 (Polish) | 8 tasks |
| Parallelizable Tasks | 42 (45%) |

**MVP Scope**: Phase 1 + Phase 2 + US1 + US5 = 37 tasks

---

## Notes

- [P] tasks = different files, no dependencies, safe to parallelize
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- MUST NOT modify Bronze or Silver Tier core logic per spec constraints
