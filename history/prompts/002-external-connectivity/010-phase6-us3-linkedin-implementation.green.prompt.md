---
id: 010
title: Phase 6 LinkedIn Post Automation Implementation
stage: green
date: 2026-01-25
surface: agent
model: claude-opus-4-5-20251101
feature: 002-external-connectivity
branch: 002-external-connectivity
user: system
command: /sp.implement
labels: ["linkedin", "mcp", "oauth", "phase-6", "us3"]
links:
  spec: specs/002-external-connectivity/spec.md
  ticket: null
  adr: null
  pr: null
files:
  - src/mcp_servers/linkedin/package.json
  - src/mcp_servers/linkedin/tsconfig.json
  - src/mcp_servers/linkedin/src/index.ts
  - src/mcp_servers/linkedin/src/credentials.ts
  - src/mcp_servers/linkedin/src/idempotency.ts
  - src/mcp_servers/linkedin/src/tools/create_post.ts
  - specs/002-external-connectivity/contracts/linkedin-mcp.json
tests:
  - TypeScript compilation check passed (tsc --noEmit)
---

## Prompt

continue to phase 6

## Response snapshot

Implemented Phase 6: User Story 3 - LinkedIn Post Automation (Priority: P3).

Created complete LinkedIn MCP server with the following structure:

**src/mcp_servers/linkedin/**
- `package.json` - Node.js project with @modelcontextprotocol/sdk, axios, better-sqlite3, keytar, zod
- `tsconfig.json` - TypeScript configuration matching Gmail MCP pattern
- `src/index.ts` - MCP server entry point with tool registration
- `src/credentials.ts` - LinkedIn OAuth2 token retrieval and refresh
- `src/idempotency.ts` - Post deduplication and rate limiting (10/day)
- `src/tools/create_post.ts` - create_post tool implementation

**Contract:**
- `specs/002-external-connectivity/contracts/linkedin-mcp.json` - Complete MCP tool definition

**Features implemented:**
1. create_post tool with content validation (max 3000 chars)
2. Visibility options: PUBLIC or CONNECTIONS
3. OAuth2 authentication via OS credential manager with token refresh
4. Idempotency check using SHA-256 hash of content+visibility+timestamp
5. Rate limiting: 10 posts per day with counter reset
6. Dry-run mode for testing without actual posting
7. Full error handling with meaningful error codes

## Outcome

- ✅ Impact: Complete LinkedIn posting capability for Silver Tier
- 🧪 Tests: TypeScript compilation passed (tsc --noEmit)
- 📁 Files: 7 files created (package.json, tsconfig.json, index.ts, credentials.ts, idempotency.ts, create_post.ts, linkedin-mcp.json)
- 🔁 Next prompts: Phase 7 Scheduled Automation Tasks, Phase 8 Resource Monitoring
- 🧠 Reflection: Followed Gmail MCP pattern for consistency; LinkedIn uses UGC Post API for content publishing

## Evaluation notes (flywheel)

- Failure modes observed: None
- Graders run and results (PASS/FAIL): TypeScript compilation PASS
- Prompt variant (if applicable): Standard implementation execution
- Next experiment (smallest change to try): Add LinkedIn OAuth setup script similar to Gmail
