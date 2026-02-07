/**
 * PM2 Ecosystem Configuration for AI Employee Silver Tier
 *
 * Manages all watcher processes:
 * - Gmail polling watcher
 * - WhatsApp webhook handler
 * - Approval folder watcher
 * - Resource monitor
 *
 * Usage:
 *   pm2 start config/pm2.config.js
 *   pm2 start config/pm2.config.js --only gmail-watcher
 *   pm2 logs
 *   pm2 monit
 *   pm2 stop all
 *
 * Implements T047 from tasks.md
 */

module.exports = {
  apps: [
    // Gmail Polling Watcher (Python)
    {
      name: "gmail-watcher",
      script: "python",
      args: ["-m", "src.watchers.gmail_watcher"],
      cwd: process.env.AI_EMPLOYEE_ROOT || ".",
      interpreter: "none",
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 5000,
      env: {
        PYTHONUNBUFFERED: "1",
        LOG_LEVEL: "INFO",
      },
      env_production: {
        PYTHONUNBUFFERED: "1",
        LOG_LEVEL: "WARNING",
      },
      // Resource limits
      max_memory_restart: "150M",
      // Logging
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      error_file: "logs/gmail-watcher-error.log",
      out_file: "logs/gmail-watcher-out.log",
      merge_logs: true,
      // Process management
      kill_timeout: 10000,
      wait_ready: true,
      listen_timeout: 30000,
    },

    // WhatsApp Webhook Handler (Python/FastAPI)
    {
      name: "whatsapp-webhook",
      script: "uvicorn",
      args: [
        "src.watchers.whatsapp_webhook:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--workers", "1",
      ],
      cwd: process.env.AI_EMPLOYEE_ROOT || ".",
      interpreter: "none",
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 5000,
      env: {
        PYTHONUNBUFFERED: "1",
        LOG_LEVEL: "INFO",
        WEBHOOK_HOST: "0.0.0.0",
        WEBHOOK_PORT: "8000",
      },
      env_production: {
        PYTHONUNBUFFERED: "1",
        LOG_LEVEL: "WARNING",
        WEBHOOK_HOST: "0.0.0.0",
        WEBHOOK_PORT: "8000",
      },
      // Resource limits
      max_memory_restart: "150M",
      // Logging
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      error_file: "logs/whatsapp-webhook-error.log",
      out_file: "logs/whatsapp-webhook-out.log",
      merge_logs: true,
      // Process management
      kill_timeout: 10000,
    },

    // Approval Folder Watcher (Python)
    {
      name: "approval-watcher",
      script: "python",
      args: ["-m", "src.watchers.approval_watcher"],
      cwd: process.env.AI_EMPLOYEE_ROOT || ".",
      interpreter: "none",
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 5000,
      env: {
        PYTHONUNBUFFERED: "1",
        LOG_LEVEL: "INFO",
      },
      env_production: {
        PYTHONUNBUFFERED: "1",
        LOG_LEVEL: "WARNING",
      },
      // Resource limits
      max_memory_restart: "100M",
      // Logging
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      error_file: "logs/approval-watcher-error.log",
      out_file: "logs/approval-watcher-out.log",
      merge_logs: true,
      // Process management
      kill_timeout: 10000,
    },

    // Resource Monitor (Python)
    {
      name: "resource-monitor",
      script: "python",
      args: ["-m", "src.watchers.resource_monitor"],
      cwd: process.env.AI_EMPLOYEE_ROOT || ".",
      interpreter: "none",
      watch: false,
      autorestart: true,
      max_restarts: 5,
      restart_delay: 10000,
      env: {
        PYTHONUNBUFFERED: "1",
        LOG_LEVEL: "INFO",
        MEMORY_BUDGET_MB: "500",
        MEMORY_ALERT_THRESHOLD_PERCENT: "80",
      },
      env_production: {
        PYTHONUNBUFFERED: "1",
        LOG_LEVEL: "WARNING",
        MEMORY_BUDGET_MB: "500",
        MEMORY_ALERT_THRESHOLD_PERCENT: "80",
      },
      // Resource limits - monitor itself should be lightweight
      max_memory_restart: "50M",
      // Logging
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      error_file: "logs/resource-monitor-error.log",
      out_file: "logs/resource-monitor-out.log",
      merge_logs: true,
      // Process management
      kill_timeout: 5000,
    },

    // Gmail MCP Server (Node.js) - Started on demand by Claude
    {
      name: "gmail-mcp",
      script: "npx",
      args: ["tsx", "src/mcp_servers/gmail/src/index.ts"],
      cwd: process.env.AI_EMPLOYEE_ROOT || ".",
      interpreter: "none",
      watch: false,
      autorestart: false,  // MCP servers are managed by clients
      env: {
        NODE_ENV: "development",
      },
      env_production: {
        NODE_ENV: "production",
      },
      // Resource limits
      max_memory_restart: "100M",
      // Logging
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      error_file: "logs/gmail-mcp-error.log",
      out_file: "logs/gmail-mcp-out.log",
      merge_logs: true,
    },

    // LinkedIn MCP Server (Node.js) - Started on demand by Claude
    {
      name: "linkedin-mcp",
      script: "npx",
      args: ["tsx", "src/mcp_servers/linkedin/src/index.ts"],
      cwd: process.env.AI_EMPLOYEE_ROOT || ".",
      interpreter: "none",
      watch: false,
      autorestart: false,  // MCP servers are managed by clients
      env: {
        NODE_ENV: "development",
      },
      env_production: {
        NODE_ENV: "production",
      },
      // Resource limits
      max_memory_restart: "100M",
      // Logging
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      error_file: "logs/linkedin-mcp-error.log",
      out_file: "logs/linkedin-mcp-out.log",
      merge_logs: true,
    },
  ],

  // Deployment configuration
  deploy: {
    production: {
      user: "ai-employee",
      host: "localhost",
      ref: "origin/main",
      repo: "git@github.com:your-org/ai-employee.git",
      path: "/opt/ai-employee",
      "pre-deploy-local": "",
      "post-deploy": "pip install -r requirements.txt && pm2 reload config/pm2.config.js --env production",
      "pre-setup": "",
    },
  },
};
