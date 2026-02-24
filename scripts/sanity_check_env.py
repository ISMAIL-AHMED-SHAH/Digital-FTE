#!/usr/bin/env python3
"""Environment Sanity Check for Digital FTE Gold Tier.

Validates all required environment variables, .env file structure,
and OS credential manager entries before system startup.

Usage:
    python scripts/sanity_check_env.py [--tier bronze|silver|gold]

Exit codes:
    0 - All checks passed
    1 - Critical failures found
    2 - Warnings found (non-blocking)
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from dotenv import load_dotenv
except ImportError:
    print("❌ python-dotenv not installed. Run: pip install python-dotenv")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)
logger = logging.getLogger(__name__)


class ValidationResult:
    """Tracks validation results."""

    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.passed: list[str] = []

    def add_error(self, message: str):
        """Add a critical error."""
        self.errors.append(message)

    def add_warning(self, message: str):
        """Add a non-critical warning."""
        self.warnings.append(message)

    def add_pass(self, message: str):
        """Add a successful check."""
        self.passed.append(message)

    def is_success(self) -> bool:
        """Check if validation passed (no errors)."""
        return len(self.errors) == 0

    def has_warnings(self) -> bool:
        """Check if there are warnings."""
        return len(self.warnings) > 0


# Required environment variables by tier
ENV_REQUIREMENTS = {
    "bronze": {
        "required": [
            "VAULT_PATH",
            "IDEMPOTENCY_DB_PATH",
        ],
        "optional": [
            "DRY_RUN",
            "DEV_MODE",
        ]
    },
    "silver": {
        "required": [
            "VAULT_PATH",
            "IDEMPOTENCY_DB_PATH",
            "GMAIL_CLIENT_ID",
            "GMAIL_CLIENT_SECRET",
            "LINKEDIN_CLIENT_ID",
            "LINKEDIN_CLIENT_SECRET",
            "WHATSAPP_PHONE_NUMBER_ID",
            "WHATSAPP_BUSINESS_ACCOUNT_ID",
            "WHATSAPP_APP_SECRET",
            "WHATSAPP_WEBHOOK_VERIFY_TOKEN",
            "WEBHOOK_PORT",
            "WEBHOOK_PUBLIC_URL",
        ],
        "optional": [
            "DRY_RUN",
            "DEV_MODE",
        ]
    },
    "gold": {
        "required": [
            # Bronze/Silver requirements
            "VAULT_PATH",
            "IDEMPOTENCY_DB_PATH",
            "GMAIL_CLIENT_ID",
            "GMAIL_CLIENT_SECRET",
            "LINKEDIN_CLIENT_ID",
            "LINKEDIN_CLIENT_SECRET",
            "WHATSAPP_PHONE_NUMBER_ID",
            "WHATSAPP_BUSINESS_ACCOUNT_ID",
            "WHATSAPP_APP_SECRET",
            "WHATSAPP_WEBHOOK_VERIFY_TOKEN",
            "WEBHOOK_PORT",
            "WEBHOOK_PUBLIC_URL",
            # Gold Tier specific
            "ODOO_HOST",
            "ODOO_PORT",
            "ODOO_DATABASE",
            "ODOO_USERNAME",
            "META_APP_ID",
            "FB_PAGE_ID",
            "IG_USER_ID",
            "TWITTER_API_KEY",
            "TWITTER_ACCESS_TOKEN",
        ],
        "optional": [
            "DRY_RUN",
            "DEV_MODE",
            "GOLD_TIER_ENABLED",
            "ODOO_INTEGRATION_ENABLED",
            "CEO_BRIEFING_ENABLED",
            "RALPH_WIGGUM_ENABLED",
        ]
    }
}


# Required OS credential manager entries by tier
CREDENTIAL_REQUIREMENTS = {
    "bronze": [],
    "silver": [
        ("gmail", ["access_token", "refresh_token"]),
        ("linkedin", ["access_token", "refresh_token"]),
        ("whatsapp", ["access_token"]),
    ],
    "gold": [
        # Silver requirements
        ("gmail", ["access_token", "refresh_token"]),
        ("linkedin", ["access_token", "refresh_token"]),
        ("whatsapp", ["access_token"]),
        # Gold Tier specific
        ("odoo", ["api_key"]),
        ("facebook", ["page_access_token"]),
        ("instagram", ["access_token"]),
        ("twitter", ["api_secret", "access_token_secret", "bearer_token"]),
    ]
}


def check_env_file(result: ValidationResult) -> dict[str, str]:
    """Check if .env file exists and load it."""
    env_path = project_root / "config" / ".env"

    if not env_path.exists():
        result.add_error(f"❌ .env file not found at: {env_path}")
        result.add_error("   → Create it by copying config/.env.example to config/.env")
        return {}

    result.add_pass(f"✅ .env file exists at: {env_path}")

    # Load environment variables
    load_dotenv(env_path)

    # Return all environment variables as dict
    return dict(os.environ)


def check_env_variables(env_vars: dict[str, str], tier: str, result: ValidationResult):
    """Check required environment variables."""
    requirements = ENV_REQUIREMENTS.get(tier, {})
    required = requirements.get("required", [])
    optional = requirements.get("optional", [])

    logger.info(f"\n📋 Checking {tier.upper()} Tier Environment Variables...")

    # Check required variables
    for var in required:
        if var not in env_vars or not env_vars[var].strip():
            result.add_error(f"❌ Missing required variable: {var}")
        else:
            value = env_vars[var]
            # Mask sensitive values
            if any(x in var.lower() for x in ["secret", "token", "key", "password"]):
                display_value = value[:8] + "..." if len(value) > 8 else "***"
            else:
                display_value = value
            result.add_pass(f"✅ {var} = {display_value}")

    # Check optional variables
    for var in optional:
        if var not in env_vars:
            result.add_warning(f"⚠️  Optional variable not set: {var} (will use default)")
        else:
            result.add_pass(f"✅ {var} = {env_vars[var]}")


def check_paths(env_vars: dict[str, str], result: ValidationResult):
    """Check that required paths exist."""
    logger.info("\n📁 Checking Filesystem Paths...")

    # Check VAULT_PATH
    vault_path = env_vars.get("VAULT_PATH", "")
    if vault_path:
        vault = Path(vault_path)
        if not vault.exists():
            result.add_error(f"❌ VAULT_PATH does not exist: {vault_path}")
        elif not vault.is_dir():
            result.add_error(f"❌ VAULT_PATH is not a directory: {vault_path}")
        else:
            result.add_pass(f"✅ VAULT_PATH exists: {vault_path}")

    # Check IDEMPOTENCY_DB_PATH parent directory
    db_path = env_vars.get("IDEMPOTENCY_DB_PATH", "data/idempotency.db")
    db_file = project_root / db_path
    db_dir = db_file.parent

    if not db_dir.exists():
        result.add_warning(f"⚠️  Database directory does not exist: {db_dir}")
        result.add_warning(f"   → Will be created automatically on first run")
    else:
        result.add_pass(f"✅ Database directory exists: {db_dir}")


def check_credentials(tier: str, env_vars: dict[str, str], result: ValidationResult):
    """Check OS credential manager entries."""
    logger.info("\n🔐 Checking OS Credential Manager Entries...")

    dry_run = env_vars.get("DRY_RUN", "false").lower() == "true"
    odoo_only = (
        env_vars.get("ODOO_INTEGRATION_ENABLED", "false").lower() == "true"
        and env_vars.get("CEO_BRIEFING_ENABLED", "false").lower() != "true"
        and env_vars.get("RALPH_WIGGUM_ENABLED", "false").lower() != "true"
    )

    # Services that can be skipped in dry-run or Odoo-only mode
    skip_if_dry_run = {"gmail", "linkedin", "whatsapp", "facebook", "instagram", "twitter"}

    try:
        from src.common.credentials import get_credential_manager
        manager = get_credential_manager()
    except Exception as e:
        result.add_error(f"❌ Failed to initialize credential manager: {e}")
        return

    requirements = CREDENTIAL_REQUIREMENTS.get(tier, [])

    if not requirements:
        result.add_pass("✅ No credential manager entries required for Bronze Tier")
        return

    for service, keys in requirements:
        # In dry-run/odoo-only mode, skip non-Odoo credentials as warnings
        if dry_run and odoo_only and service in skip_if_dry_run:
            result.add_warning(f"⚠️  Skipping '{service}' credentials (DRY_RUN + Odoo-only mode)")
            continue

        # Try to retrieve token
        try:
            token = manager.get_token(service)
            if token:
                result.add_pass(f"✅ Credential found for service: {service}")
                # Check for required keys
                for key in keys:
                    if key not in token:
                        result.add_warning(f"⚠️  Service '{service}' missing key: {key}")
            else:
                result.add_error(f"❌ No credentials found for service: {service}")
                result.add_error(f"   → Run: python scripts/setup_{service}_oauth.py")
        except Exception as e:
            result.add_error(f"❌ Failed to check credentials for {service}: {e}")


def check_odoo_connectivity(env_vars: dict[str, str], result: ValidationResult):
    """Check Odoo connectivity (if Gold Tier and Odoo enabled)."""
    if env_vars.get("ODOO_INTEGRATION_ENABLED", "false").lower() != "true":
        result.add_pass("✅ Odoo integration disabled, skipping connectivity check")
        return

    logger.info("\n🏢 Checking Odoo Connectivity...")

    host = env_vars.get("ODOO_HOST", "localhost")
    port = env_vars.get("ODOO_PORT", "8069")

    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        connection_result = sock.connect_ex((host, int(port)))
        sock.close()

        if connection_result == 0:
            result.add_pass(f"✅ Odoo server reachable at {host}:{port}")
        else:
            result.add_warning(f"⚠️  Cannot connect to Odoo at {host}:{port}")
            result.add_warning(f"   → Ensure Odoo is running or set DRY_RUN=true for testing")
    except Exception as e:
        result.add_warning(f"⚠️  Failed to check Odoo connectivity: {e}")


def check_feature_flags(env_vars: dict[str, str], tier: str, result: ValidationResult):
    """Check feature flag consistency."""
    if tier != "gold":
        return

    logger.info("\n🎛️  Checking Feature Flags...")

    gold_enabled = env_vars.get("GOLD_TIER_ENABLED", "false").lower() == "true"
    odoo_enabled = env_vars.get("ODOO_INTEGRATION_ENABLED", "false").lower() == "true"
    ceo_enabled = env_vars.get("CEO_BRIEFING_ENABLED", "false").lower() == "true"
    ralph_enabled = env_vars.get("RALPH_WIGGUM_ENABLED", "false").lower() == "true"

    if gold_enabled:
        result.add_pass("✅ GOLD_TIER_ENABLED = true")
    else:
        result.add_warning("⚠️  GOLD_TIER_ENABLED = false (Gold features disabled)")

    if odoo_enabled:
        result.add_pass("✅ ODOO_INTEGRATION_ENABLED = true")
    if ceo_enabled:
        result.add_pass("✅ CEO_BRIEFING_ENABLED = true")
    if ralph_enabled:
        result.add_pass("✅ RALPH_WIGGUM_ENABLED = true")


def print_summary(result: ValidationResult):
    """Print validation summary."""
    logger.info("\n" + "=" * 70)
    logger.info("📊 VALIDATION SUMMARY")
    logger.info("=" * 70)

    logger.info(f"\n✅ Passed: {len(result.passed)}")
    logger.info(f"⚠️  Warnings: {len(result.warnings)}")
    logger.info(f"❌ Errors: {len(result.errors)}")

    if result.errors:
        logger.info("\n🚨 CRITICAL ERRORS (must fix before proceeding):")
        for i, error in enumerate(result.errors, 1):
            logger.info(f"  {i}. {error}")

    if result.warnings:
        logger.info("\n⚠️  WARNINGS (recommended to fix):")
        for i, warning in enumerate(result.warnings, 1):
            logger.info(f"  {i}. {warning}")

    logger.info("\n" + "=" * 70)

    if result.is_success():
        if result.has_warnings():
            logger.info("✅ VALIDATION PASSED (with warnings)")
            logger.info("🟢 System can start, but review warnings above")
        else:
            logger.info("✅ VALIDATION PASSED")
            logger.info("🟢 All checks passed - system ready to start!")
    else:
        logger.info("❌ VALIDATION FAILED")
        logger.info("🔴 Fix errors above before starting the system")
        logger.info("🔴 DO NOT START PM2 until validation passes")

    logger.info("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Validate environment configuration for Digital FTE"
    )
    parser.add_argument(
        "--tier",
        choices=["bronze", "silver", "gold"],
        default="gold",
        help="Tier to validate (default: gold)"
    )
    args = parser.parse_args()

    logger.info("=" * 70)
    logger.info(f"🔍 DIGITAL FTE ENVIRONMENT VALIDATION - {args.tier.upper()} TIER")
    logger.info("=" * 70)

    result = ValidationResult()

    # Step 1: Check .env file
    logger.info("\n📄 Step 1: Checking .env file...")
    env_vars = check_env_file(result)

    if not result.is_success():
        print_summary(result)
        return 1

    # Step 2: Check environment variables
    logger.info("\n📋 Step 2: Checking environment variables...")
    check_env_variables(env_vars, args.tier, result)

    # Step 3: Check filesystem paths
    logger.info("\n📁 Step 3: Checking filesystem paths...")
    check_paths(env_vars, result)

    # Step 4: Check OS credential manager
    logger.info("\n🔐 Step 4: Checking OS credential manager...")
    check_credentials(args.tier, env_vars, result)

    # Step 5: Check Odoo connectivity (Gold Tier only)
    if args.tier == "gold":
        logger.info("\n🏢 Step 5: Checking Odoo connectivity...")
        check_odoo_connectivity(env_vars, result)

        logger.info("\n🎛️  Step 6: Checking feature flags...")
        check_feature_flags(env_vars, args.tier, result)

    # Print summary
    print_summary(result)

    # Exit with appropriate code
    if not result.is_success():
        return 1
    elif result.has_warnings():
        return 2
    else:
        return 0


if __name__ == "__main__":
    sys.exit(main())
