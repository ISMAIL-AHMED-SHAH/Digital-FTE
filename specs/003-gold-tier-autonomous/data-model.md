# Data Model: Gold Tier - Autonomous Employee

**Branch**: `003-gold-tier-autonomous` | **Date**: 2026-02-05 | **Plan**: [plan.md](./plan.md)

This document defines the entity schemas for Gold Tier implementation. All entities extend or complement Silver Tier data models.

---

## 1. OdooConnection

Represents a connection configuration to an Odoo Community instance.

```yaml
OdooConnection:
  description: Configuration for connecting to Odoo ERP via JSON-RPC
  properties:
    id:
      type: string
      format: uuid
      description: Unique connection identifier
    name:
      type: string
      description: Human-readable connection name (e.g., "Production Odoo")
    host:
      type: string
      description: Odoo server hostname or IP
      example: "localhost"
    port:
      type: integer
      default: 8069
      description: Odoo server port
    database:
      type: string
      description: Odoo database name
    username:
      type: string
      description: Odoo username for authentication
    api_key_ref:
      type: string
      description: Reference to API key in OS credential manager
      example: "odoo_api_key_production"
    timeout_seconds:
      type: integer
      default: 30
      description: Connection timeout (per spec clarification)
    max_retries:
      type: integer
      default: 3
      description: Maximum retry attempts before queuing
    status:
      type: string
      enum: [connected, disconnected, error, unknown]
      description: Current connection status
    last_connected:
      type: string
      format: date-time
      nullable: true
      description: Timestamp of last successful connection
    error_message:
      type: string
      nullable: true
      description: Last error message if status is error
  required:
    - id
    - name
    - host
    - database
    - username
    - api_key_ref
```

---

## 2. Invoice

Represents a customer invoice created via Odoo MCP.

```yaml
Invoice:
  description: Customer invoice record (mirrors Odoo account.move)
  properties:
    id:
      type: string
      format: uuid
      description: Local unique identifier
    odoo_id:
      type: integer
      nullable: true
      description: Odoo account.move ID (null until created in Odoo)
    invoice_number:
      type: string
      nullable: true
      description: Odoo invoice number (e.g., "INV/2026/00001")
    partner_id:
      type: integer
      description: Odoo partner (customer) ID
    partner_name:
      type: string
      description: Customer name for display
    invoice_date:
      type: string
      format: date
      description: Invoice date (YYYY-MM-DD)
    due_date:
      type: string
      format: date
      nullable: true
      description: Payment due date
    lines:
      type: array
      items:
        $ref: "#/InvoiceLine"
      description: Invoice line items
    amount_untaxed:
      type: number
      format: decimal
      description: Subtotal before tax
    amount_tax:
      type: number
      format: decimal
      description: Total tax amount
    amount_total:
      type: number
      format: decimal
      description: Total invoice amount
    amount_residual:
      type: number
      format: decimal
      description: Remaining unpaid amount
    state:
      type: string
      enum: [draft, pending_approval, posted, paid, cancelled]
      description: Invoice state
    notes:
      type: string
      nullable: true
      description: Internal notes
    vault_reference:
      type: string
      description: Path to approval file in vault
      example: "/Vault/Needs_Approval/invoice_2026-02-05_001.md"
    created_at:
      type: string
      format: date-time
    updated_at:
      type: string
      format: date-time
  required:
    - id
    - partner_id
    - partner_name
    - invoice_date
    - lines
    - amount_total
    - state
    - vault_reference

InvoiceLine:
  description: Single line item on an invoice
  properties:
    description:
      type: string
      description: Line item description
    quantity:
      type: number
      format: decimal
      description: Quantity
    unit_price:
      type: number
      format: decimal
      description: Price per unit
    tax_ids:
      type: array
      items:
        type: integer
      description: Odoo tax IDs to apply
    subtotal:
      type: number
      format: decimal
      description: Line subtotal (quantity * unit_price)
  required:
    - description
    - quantity
    - unit_price
```

---

## 3. Payment

Represents a payment entry created via Odoo MCP.

```yaml
Payment:
  description: Payment record (mirrors Odoo account.payment)
  properties:
    id:
      type: string
      format: uuid
      description: Local unique identifier
    odoo_id:
      type: integer
      nullable: true
      description: Odoo account.payment ID
    partner_id:
      type: integer
      description: Odoo partner ID
    partner_name:
      type: string
      description: Partner name for display
    amount:
      type: number
      format: decimal
      description: Payment amount
    currency:
      type: string
      default: "USD"
      description: Currency code
    payment_type:
      type: string
      enum: [inbound, outbound]
      description: inbound=customer payment, outbound=vendor payment
    payment_method:
      type: string
      enum: [manual, check, bank_transfer, credit_card]
      description: Payment method
    journal_id:
      type: integer
      description: Odoo journal ID (bank/cash account)
    reference:
      type: string
      nullable: true
      description: Payment reference (e.g., invoice number, check number)
    payment_date:
      type: string
      format: date
      description: Date of payment
    state:
      type: string
      enum: [draft, pending_approval, posted, reconciled, cancelled]
      description: Payment state
    reconciled_invoice_ids:
      type: array
      items:
        type: integer
      description: Odoo invoice IDs reconciled with this payment
    vault_reference:
      type: string
      description: Path to approval file in vault
    created_at:
      type: string
      format: date-time
    updated_at:
      type: string
      format: date-time
  required:
    - id
    - partner_id
    - partner_name
    - amount
    - payment_type
    - payment_date
    - state
    - vault_reference
```

---

## 4. SocialMediaPost

Represents a post to any social media platform (extends Silver Tier pattern).

```yaml
SocialMediaPost:
  description: Social media post record for Facebook, Instagram, Twitter
  properties:
    id:
      type: string
      format: uuid
      description: Local unique identifier
    platform:
      type: string
      enum: [facebook, instagram, twitter, linkedin]
      description: Target platform
    platform_post_id:
      type: string
      nullable: true
      description: Platform-specific post ID after publishing
    platform_url:
      type: string
      format: uri
      nullable: true
      description: URL to published post
    account_id:
      type: string
      description: Platform account/page ID
    content:
      type: object
      properties:
        text:
          type: string
          description: Post text content
        media_urls:
          type: array
          items:
            type: string
            format: uri
          description: URLs to media attachments
        media_type:
          type: string
          enum: [none, image, video, carousel]
          description: Type of media attachment
        link:
          type: string
          format: uri
          nullable: true
          description: Link to share (Facebook/LinkedIn)
    scheduled_time:
      type: string
      format: date-time
      nullable: true
      description: Scheduled publish time (null for immediate)
    status:
      type: string
      enum: [draft, pending_approval, approved, publishing, published, failed, cancelled]
      description: Post status
    error_message:
      type: string
      nullable: true
      description: Error message if failed
    retry_count:
      type: integer
      default: 0
      description: Number of publish attempts
    character_count:
      type: integer
      description: Character count (for validation)
    character_limit:
      type: integer
      description: Platform character limit (280 Twitter, 63206 Facebook, 2200 Instagram)
    vault_reference:
      type: string
      description: Path to approval file in vault
    published_at:
      type: string
      format: date-time
      nullable: true
    created_at:
      type: string
      format: date-time
    updated_at:
      type: string
      format: date-time
  required:
    - id
    - platform
    - account_id
    - content
    - status
    - vault_reference

# Platform-specific constraints
PlatformConstraints:
  facebook:
    character_limit: 63206
    rate_limit_daily: 5
    requires_page_token: true
  instagram:
    character_limit: 2200
    rate_limit_daily: 3
    requires_media: true
    two_step_publish: true
  twitter:
    character_limit: 280
    rate_limit_15min: 100
    requires_oauth_1_0a: true
  linkedin:
    character_limit: 3000
    rate_limit_daily: 100
```

---

## 5. CEOBriefing

Represents a weekly CEO briefing generated by the audit system.

```yaml
CEOBriefing:
  description: Weekly CEO briefing document
  properties:
    id:
      type: string
      format: uuid
      description: Unique briefing identifier
    period_start:
      type: string
      format: date
      description: Start of reporting period
    period_end:
      type: string
      format: date
      description: End of reporting period
    generated_at:
      type: string
      format: date-time
      description: When briefing was generated
    generated_by:
      type: string
      default: "AI Employee v0.3 (Gold Tier)"
      description: Generator identification
    executive_summary:
      type: string
      description: 1-2 sentence key highlights
    revenue_data:
      type: object
      properties:
        weekly_total:
          type: number
          format: decimal
        month_to_date:
          type: number
          format: decimal
        monthly_target:
          type: number
          format: decimal
        target_percentage:
          type: number
          format: decimal
        trend:
          type: string
          enum: [on_track, ahead, behind]
        top_customers:
          type: array
          items:
            type: object
            properties:
              name:
                type: string
              revenue:
                type: number
                format: decimal
    tasks_summary:
      type: object
      properties:
        completed_count:
          type: integer
        completed_tasks:
          type: array
          items:
            type: object
            properties:
              title:
                type: string
              completed_at:
                type: string
                format: date-time
              duration_hours:
                type: number
    bottlenecks:
      type: array
      items:
        type: object
        properties:
          task_title:
            type: string
          expected_hours:
            type: number
          actual_hours:
            type: number
          delay_hours:
            type: number
          reason:
            type: string
            nullable: true
    suggestions:
      type: object
      properties:
        cost_optimization:
          type: array
          items:
            type: string
          description: Subscription and cost suggestions
        upcoming_deadlines:
          type: array
          items:
            type: object
            properties:
              title:
                type: string
              due_date:
                type: string
                format: date
              priority:
                type: string
                enum: [high, medium, low]
    vault_path:
      type: string
      description: Path to generated briefing file
      example: "/Vault/Briefings/ceo_briefing_2026-02-03.md"
    status:
      type: string
      enum: [generating, generated, delivered, acknowledged]
  required:
    - id
    - period_start
    - period_end
    - generated_at
    - executive_summary
    - revenue_data
    - tasks_summary
    - vault_path
    - status
```

---

## 6. RalphLoop

Represents an autonomous loop execution using the Ralph Wiggum pattern.

```yaml
RalphLoop:
  description: Ralph Wiggum autonomous loop execution record
  properties:
    id:
      type: string
      format: uuid
      description: Unique loop identifier
    session_id:
      type: string
      description: Claude Code session ID
    task_prompt:
      type: string
      description: Original task prompt that started the loop
    task_file_path:
      type: string
      nullable: true
      description: Path to task file in vault (for file-based completion)
    completion_strategy:
      type: string
      enum: [file_based, promise_based, hybrid]
      default: hybrid
      description: How completion is detected
    max_iterations:
      type: integer
      default: 10
      description: Maximum allowed iterations
    current_iteration:
      type: integer
      default: 0
      description: Current iteration count
    status:
      type: string
      enum: [running, completed, max_iterations_reached, error, cancelled]
      description: Loop status
    started_at:
      type: string
      format: date-time
    completed_at:
      type: string
      format: date-time
      nullable: true
    timeout_minutes:
      type: integer
      default: 30
      description: Maximum loop duration
    iteration_history:
      type: array
      items:
        type: object
        properties:
          iteration:
            type: integer
          started_at:
            type: string
            format: date-time
          ended_at:
            type: string
            format: date-time
          exit_code:
            type: integer
            description: Hook exit code (0=complete, 2=continue)
          files_modified:
            type: array
            items:
              type: string
          summary:
            type: string
            nullable: true
    completion_signal:
      type: string
      nullable: true
      description: How completion was detected (file_moved, promise_found, manual)
    error_message:
      type: string
      nullable: true
    summary_path:
      type: string
      nullable: true
      description: Path to generated completion summary
  required:
    - id
    - session_id
    - task_prompt
    - completion_strategy
    - max_iterations
    - status
    - started_at
```

---

## 7. AuditLogEntry

Represents a single audit log entry (extends Silver Tier pattern).

```yaml
AuditLogEntry:
  description: Comprehensive audit log entry for all actions
  properties:
    id:
      type: string
      format: uuid
      description: Unique entry identifier
    timestamp:
      type: string
      format: date-time
      description: When action occurred
    action_type:
      type: string
      enum:
        # Odoo actions
        - odoo.invoice.create
        - odoo.invoice.post
        - odoo.payment.create
        - odoo.payment.post
        - odoo.query.financial_summary
        # Social actions
        - social.facebook.post
        - social.instagram.publish
        - social.twitter.tweet
        - social.linkedin.post
        # Email actions (from Silver)
        - email.send
        - email.draft
        # Approval actions
        - approval.request
        - approval.granted
        - approval.denied
        # System actions
        - system.watchdog.restart
        - system.error.quarantine
        - system.loop.iteration
        - system.briefing.generate
      description: Type of action performed
    actor:
      type: string
      description: Who/what performed the action
      example: "AI Employee", "User", "Watchdog"
    target:
      type: string
      description: What was acted upon
      example: "invoice_001", "facebook_post_123"
    parameters:
      type: object
      additionalProperties: true
      description: Action-specific parameters
    approval:
      type: object
      nullable: true
      properties:
        required:
          type: boolean
        status:
          type: string
          enum: [pending, approved, denied, not_required]
        approved_by:
          type: string
          nullable: true
        approved_at:
          type: string
          format: date-time
          nullable: true
    result:
      type: object
      properties:
        success:
          type: boolean
        data:
          type: object
          additionalProperties: true
          nullable: true
        error_code:
          type: string
          nullable: true
        error_message:
          type: string
          nullable: true
    duration_ms:
      type: integer
      description: Action duration in milliseconds
    correlation_id:
      type: string
      nullable: true
      description: ID linking related actions
  required:
    - id
    - timestamp
    - action_type
    - actor
    - target
    - result
```

---

## 8. QuarantinedFile

Represents a file moved to quarantine due to errors.

```yaml
QuarantinedFile:
  description: File quarantined due to processing errors
  properties:
    id:
      type: string
      format: uuid
      description: Unique quarantine record ID
    original_path:
      type: string
      description: Original file path before quarantine
    quarantine_path:
      type: string
      description: Current path in /Quarantine folder
    filename:
      type: string
      description: Original filename
    error_type:
      type: string
      enum:
        - parse_error
        - validation_error
        - processing_error
        - integrity_error
        - permission_error
        - unknown_error
      description: Category of error
    error_message:
      type: string
      description: Detailed error message
    error_stack:
      type: string
      nullable: true
      description: Stack trace if available
    file_hash:
      type: string
      description: SHA-256 hash of file contents
    file_size_bytes:
      type: integer
      description: File size
    quarantined_at:
      type: string
      format: date-time
    quarantined_by:
      type: string
      description: Component that quarantined the file
    resolution_status:
      type: string
      enum: [pending, reviewed, fixed, deleted, restored]
      default: pending
    resolution_notes:
      type: string
      nullable: true
    resolved_at:
      type: string
      format: date-time
      nullable: true
    resolved_by:
      type: string
      nullable: true
  required:
    - id
    - original_path
    - quarantine_path
    - filename
    - error_type
    - error_message
    - file_hash
    - quarantined_at
    - quarantined_by
    - resolution_status
```

---

## Entity Relationships

```
┌─────────────────┐     creates     ┌─────────────────┐
│ OdooConnection  │───────────────▶ │     Invoice     │
└─────────────────┘                 └─────────────────┘
        │                                   │
        │ creates                           │ reconciled_with
        ▼                                   ▼
┌─────────────────┐                 ┌─────────────────┐
│     Payment     │◀────────────────│     Payment     │
└─────────────────┘                 └─────────────────┘

┌─────────────────┐     generates   ┌─────────────────┐
│   CEOBriefing   │◀────────────────│  Invoice/Task   │
└─────────────────┘                 │     Data        │
                                    └─────────────────┘

┌─────────────────┐     publishes   ┌─────────────────┐
│ SocialMediaPost │◀────────────────│   MCP Server    │
└─────────────────┘                 │ (FB/IG/TW/LI)   │
                                    └─────────────────┘

┌─────────────────┐     tracks      ┌─────────────────┐
│   RalphLoop     │◀────────────────│ Claude Session  │
└─────────────────┘                 └─────────────────┘
        │
        │ logs
        ▼
┌─────────────────┐
│ AuditLogEntry   │
└─────────────────┘

┌─────────────────┐     contains    ┌─────────────────┐
│ QuarantinedFile │◀────────────────│  Error Handler  │
└─────────────────┘                 └─────────────────┘
```

---

## Storage Locations

| Entity | Storage | Retention |
|--------|---------|-----------|
| OdooConnection | `config/gold_tier.yaml` | Permanent |
| Invoice | SQLite + Odoo | 7 years (Odoo) |
| Payment | SQLite + Odoo | 7 years (Odoo) |
| SocialMediaPost | SQLite | 90 days |
| CEOBriefing | `/Vault/Briefings/` | 1 year |
| RalphLoop | SQLite | 30 days |
| AuditLogEntry | `/Vault/Logs/YYYY-MM-DD.json` | 90 days |
| QuarantinedFile | `/Vault/Quarantine/` | Until resolved |
