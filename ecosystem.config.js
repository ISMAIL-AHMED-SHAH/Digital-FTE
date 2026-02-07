/**
 * PM2 Ecosystem Configuration (T029)
 *
 * Process management configuration for AI Employee services.
 * Manages all watchers, MCP servers, and background tasks.
 *
 * Usage:
 *   pm2 start ecosystem.config.js
 *   pm2 start ecosystem.config.js --only odoo-mcp
 *   pm2 stop all
 *   pm2 logs
 */

module.exports = {
  apps: [
    // ==========================================================================
    // Bronze Tier - File Watcher
    // ==========================================================================
    {
      name: 'file-watcher',
      script: 'python',
      args: '-m src.watchers.file_watcher',
      cwd: './',
      interpreter: 'none',
      env: {
        PYTHONPATH: '.',
        VAULT_PATH: './vault',
        DROP_FOLDER: './drop',
      },
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 5000,
      error_file: './logs/file-watcher-error.log',
      out_file: './logs/file-watcher-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    },

    // ==========================================================================
    // Gold Tier - Odoo MCP Server
    // ==========================================================================
    {
      name: 'odoo-mcp',
      script: 'node',
      args: 'dist/index.js',
      cwd: './src/mcp_servers/odoo',
      interpreter: 'none',
      env: {
        NODE_ENV: 'production',
        // Odoo credentials from .env
        ODOO_URL: process.env.ODOO_URL,
        ODOO_DATABASE: process.env.ODOO_DATABASE,
        ODOO_USERNAME: process.env.ODOO_USERNAME,
        ODOO_PASSWORD: process.env.ODOO_PASSWORD,
        ODOO_API_KEY: process.env.ODOO_API_KEY,
        VAULT_PATH: './vault',
      },
      watch: false,
      autorestart: true,
      max_restarts: 5,
      restart_delay: 10000,
      error_file: './logs/odoo-mcp-error.log',
      out_file: './logs/odoo-mcp-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      // Don't start automatically - Claude Code manages MCP servers
      instances: 1,
      exec_mode: 'fork',
    },

    // ==========================================================================
    // Gold Tier - Facebook MCP Server (T051)
    // ==========================================================================
    {
      name: 'facebook-mcp',
      script: 'node',
      args: 'dist/index.js',
      cwd: './src/mcp_servers/facebook',
      interpreter: 'none',
      env: {
        NODE_ENV: 'production',
        META_APP_ID: process.env.META_APP_ID,
        META_APP_SECRET: process.env.META_APP_SECRET,
        META_ACCESS_TOKEN: process.env.META_ACCESS_TOKEN,
        META_PAGE_ID: process.env.META_PAGE_ID,
        VAULT_PATH: './vault',
      },
      watch: false,
      autorestart: true,
      max_restarts: 5,
      restart_delay: 10000,
      error_file: './logs/facebook-mcp-error.log',
      out_file: './logs/facebook-mcp-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      instances: 1,
      exec_mode: 'fork',
    },

    // ==========================================================================
    // Gold Tier - Instagram MCP Server (T051)
    // ==========================================================================
    {
      name: 'instagram-mcp',
      script: 'node',
      args: 'dist/index.js',
      cwd: './src/mcp_servers/instagram',
      interpreter: 'none',
      env: {
        NODE_ENV: 'production',
        META_APP_ID: process.env.META_APP_ID,
        META_APP_SECRET: process.env.META_APP_SECRET,
        META_ACCESS_TOKEN: process.env.META_ACCESS_TOKEN,
        INSTAGRAM_BUSINESS_ACCOUNT_ID: process.env.INSTAGRAM_BUSINESS_ACCOUNT_ID,
        VAULT_PATH: './vault',
      },
      watch: false,
      autorestart: true,
      max_restarts: 5,
      restart_delay: 10000,
      error_file: './logs/instagram-mcp-error.log',
      out_file: './logs/instagram-mcp-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      instances: 1,
      exec_mode: 'fork',
    },

    // ==========================================================================
    // Gold Tier - Twitter MCP Server (T061)
    // ==========================================================================
    {
      name: 'twitter-mcp',
      script: 'node',
      args: 'dist/index.js',
      cwd: './src/mcp_servers/twitter',
      interpreter: 'none',
      env: {
        NODE_ENV: 'production',
        TWITTER_API_KEY: process.env.TWITTER_API_KEY,
        TWITTER_API_SECRET: process.env.TWITTER_API_SECRET,
        TWITTER_ACCESS_TOKEN: process.env.TWITTER_ACCESS_TOKEN,
        TWITTER_ACCESS_SECRET: process.env.TWITTER_ACCESS_SECRET,
        TWITTER_BEARER_TOKEN: process.env.TWITTER_BEARER_TOKEN,
        VAULT_PATH: './vault',
      },
      watch: false,
      autorestart: true,
      max_restarts: 5,
      restart_delay: 10000,
      error_file: './logs/twitter-mcp-error.log',
      out_file: './logs/twitter-mcp-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      instances: 1,
      exec_mode: 'fork',
    },

    // ==========================================================================
    // Gold Tier - Action Queue Processor
    // ==========================================================================
    {
      name: 'action-queue',
      script: 'python',
      args: '-m src.orchestrator.queue_processor',
      cwd: './',
      interpreter: 'none',
      env: {
        PYTHONPATH: '.',
        QUEUE_PATH: './data/action_queue.json',
        PROCESSING_INTERVAL: '60',
      },
      watch: false,
      autorestart: true,
      max_restarts: 10,
      restart_delay: 5000,
      error_file: './logs/action-queue-error.log',
      out_file: './logs/action-queue-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    },

    // ==========================================================================
    // Gold Tier - Watchdog Process Monitor
    // ==========================================================================
    {
      name: 'watchdog',
      script: 'python',
      args: '-m src.orchestrator.watchdog_runner',
      cwd: './',
      interpreter: 'none',
      env: {
        PYTHONPATH: '.',
        LOG_DIR: './logs',
      },
      watch: false,
      autorestart: true,
      max_restarts: 3,
      restart_delay: 10000,
      error_file: './logs/watchdog-error.log',
      out_file: './logs/watchdog-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    },

    // ==========================================================================
    // Gold Tier - Log Maintenance (Scheduled)
    // ==========================================================================
    {
      name: 'log-maintenance',
      script: 'python',
      args: '-m src.tasks.log_maintenance',
      cwd: './',
      interpreter: 'none',
      env: {
        PYTHONPATH: '.',
        LOG_DIR: './logs',
        RETENTION_DAYS: '90',
        COMPRESSION_DAYS: '30',
      },
      cron_restart: '0 3 * * *', // Run at 3 AM daily
      autorestart: false,
      error_file: './logs/log-maintenance-error.log',
      out_file: './logs/log-maintenance-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    },

    // ==========================================================================
    // Gold Tier - CEO Briefing (Scheduled)
    // ==========================================================================
    {
      name: 'ceo-briefing',
      script: 'python',
      args: '-m src.tasks.ceo_briefing',
      cwd: './',
      interpreter: 'none',
      env: {
        PYTHONPATH: '.',
        VAULT_PATH: './vault',
      },
      cron_restart: '0 23 * * 0', // Run Sunday 11 PM
      autorestart: false,
      error_file: './logs/ceo-briefing-error.log',
      out_file: './logs/ceo-briefing-out.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    },
  ],

  // Deployment configuration (for remote servers)
  deploy: {
    production: {
      user: 'deploy',
      host: ['server1.example.com'],
      ref: 'origin/main',
      repo: 'git@github.com:user/ai-employee.git',
      path: '/var/www/ai-employee',
      'post-deploy': 'npm install && pm2 reload ecosystem.config.js --env production',
    },
  },
};
