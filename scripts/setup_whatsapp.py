#!/usr/bin/env python3
"""WhatsApp Business API Setup Script for Silver Tier.

This script guides you through setting up the WhatsApp Business API webhook
and provides the webhook URL for Meta Business API configuration.

Prerequisites:
1. A Meta Business account at https://business.facebook.com
2. A WhatsApp Business account linked to your Meta Business account
3. Access to Meta for Developers at https://developers.facebook.com
4. A phone number registered with WhatsApp Business

Usage:
    python scripts/setup_whatsapp.py

    # Generate webhook verify token
    python scripts/setup_whatsapp.py --generate-token

    # Test webhook signature validation
    python scripts/setup_whatsapp.py --test-signature

    # Output JSON for automation
    python scripts/setup_whatsapp.py --json
"""

import argparse
import hashlib
import hmac
import json
import logging
import os
import secrets
import socket
import sys
from pathlib import Path
from urllib.parse import urljoin

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load environment variables
load_dotenv(project_root / "config" / ".env")
load_dotenv(project_root / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_local_ip() -> str:
    """Get the local IP address of this machine."""
    try:
        # Create a socket to determine the local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "localhost"


def generate_verify_token() -> str:
    """Generate a secure webhook verify token.

    Returns:
        32-character hex token
    """
    return secrets.token_hex(16)


def get_webhook_config() -> dict:
    """Get webhook configuration from environment and defaults.

    Returns:
        Dict with webhook configuration
    """
    host = os.environ.get("WEBHOOK_HOST", "0.0.0.0")
    port = int(os.environ.get("WEBHOOK_PORT", "8000"))
    verify_token = os.environ.get("WHATSAPP_VERIFY_TOKEN", "")
    app_secret = os.environ.get("WHATSAPP_APP_SECRET", "")
    public_url = os.environ.get("WEBHOOK_PUBLIC_URL", "")

    # If no public URL, construct one from local IP
    if not public_url:
        local_ip = get_local_ip()
        public_url = f"http://{local_ip}:{port}"

    return {
        "host": host,
        "port": port,
        "verify_token": verify_token,
        "app_secret": app_secret,
        "public_url": public_url,
        "webhook_path": "/webhooks/whatsapp",
        "full_webhook_url": urljoin(public_url, "/webhooks/whatsapp")
    }


def test_signature_validation(app_secret: str) -> bool:
    """Test webhook signature validation with a sample payload.

    Args:
        app_secret: WhatsApp app secret

    Returns:
        True if validation works correctly
    """
    if not app_secret:
        logger.error("WHATSAPP_APP_SECRET not set in environment")
        return False

    # Sample test payload
    test_payload = json.dumps({
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "test_account_id",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "messages": []
                }
            }]
        }]
    }).encode("utf-8")

    # Generate valid signature
    expected_signature = hmac.new(
        key=app_secret.encode("utf-8"),
        msg=test_payload,
        digestmod=hashlib.sha256
    ).hexdigest()

    # Test validation
    from src.watchers.whatsapp_webhook import validate_signature

    # Test with valid signature
    signature_header = f"sha256={expected_signature}"
    if not validate_signature(test_payload, signature_header, app_secret):
        logger.error("Signature validation FAILED for valid signature")
        return False

    logger.info("Valid signature correctly accepted")

    # Test with invalid signature
    invalid_header = f"sha256={'0' * 64}"
    if validate_signature(test_payload, invalid_header, app_secret):
        logger.error("Signature validation FAILED to reject invalid signature")
        return False

    logger.info("Invalid signature correctly rejected")

    return True


def update_env_file(verify_token: str | None = None, app_secret: str | None = None) -> Path:
    """Update .env file with WhatsApp configuration.

    Args:
        verify_token: Webhook verify token to set
        app_secret: App secret to set

    Returns:
        Path to the .env file
    """
    env_path = project_root / ".env"

    # Read existing content
    existing_lines = []
    if env_path.exists():
        with open(env_path, "r") as f:
            existing_lines = f.readlines()

    # Parse existing values
    existing_vars = {}
    for line in existing_lines:
        if "=" in line and not line.strip().startswith("#"):
            key = line.split("=")[0].strip()
            existing_vars[key] = line

    # Update values
    if verify_token:
        existing_vars["WHATSAPP_VERIFY_TOKEN"] = f"WHATSAPP_VERIFY_TOKEN={verify_token}\n"

    if app_secret:
        existing_vars["WHATSAPP_APP_SECRET"] = f"WHATSAPP_APP_SECRET={app_secret}\n"

    # Reconstruct file
    output_lines = []
    seen_keys = set()

    for line in existing_lines:
        if "=" in line and not line.strip().startswith("#"):
            key = line.split("=")[0].strip()
            if key in existing_vars and key not in seen_keys:
                output_lines.append(existing_vars[key])
                seen_keys.add(key)
        else:
            output_lines.append(line)

    # Add new vars not in original file
    for key, value in existing_vars.items():
        if key not in seen_keys:
            if output_lines and not output_lines[-1].endswith("\n"):
                output_lines.append("\n")
            output_lines.append(value)
            seen_keys.add(key)

    # Write back
    with open(env_path, "w") as f:
        f.writelines(output_lines)

    return env_path


def print_setup_instructions(config: dict, json_output: bool = False):
    """Print setup instructions for WhatsApp Business API.

    Args:
        config: Webhook configuration dict
        json_output: If True, output JSON instead of formatted text
    """
    if json_output:
        print(json.dumps(config, indent=2))
        return

    print()
    print("=" * 70)
    print(" WhatsApp Business API Setup Instructions")
    print("=" * 70)
    print()

    print("STEP 1: Start the Webhook Server")
    print("-" * 40)
    print()
    print("Run the following command to start the webhook handler:")
    print()
    print(f"  uvicorn src.watchers.whatsapp_webhook:app --host {config['host']} --port {config['port']}")
    print()
    print("Or as a module:")
    print()
    print("  python -m src.watchers.whatsapp_webhook")
    print()

    print("STEP 2: Configure Webhook in Meta Developer Console")
    print("-" * 40)
    print()
    print("1. Go to https://developers.facebook.com/apps/")
    print("2. Select your WhatsApp Business app")
    print("3. Navigate to: WhatsApp > Configuration > Webhook")
    print("4. Click 'Edit' on the Webhook section")
    print()
    print("5. Enter the following values:")
    print()
    print(f"   Callback URL:     {config['full_webhook_url']}")
    print()

    if config['verify_token']:
        print(f"   Verify Token:     {config['verify_token']}")
    else:
        print("   Verify Token:     [Not set - generate one with --generate-token]")
    print()

    print("6. Click 'Verify and Save'")
    print()
    print("7. Subscribe to Webhook Fields:")
    print("   - messages")
    print("   - messaging_postbacks (optional)")
    print()

    print("STEP 3: Configure App Secret for Signature Validation")
    print("-" * 40)
    print()
    print("1. Go to your app's Settings > Basic in Meta Developer Console")
    print("2. Copy the 'App Secret' value")
    print("3. Add to your .env file:")
    print()
    print("   WHATSAPP_APP_SECRET=your_app_secret_here")
    print()

    if not config['app_secret']:
        print("   [WARNING] WHATSAPP_APP_SECRET is not currently set!")
        print("   Signature validation will be skipped until this is configured.")
        print()

    print("STEP 4: Test the Webhook")
    print("-" * 40)
    print()
    print("1. Send a test message to your WhatsApp Business number")
    print("2. Check the webhook server logs for incoming messages")
    print("3. Verify action files are created in your vault's Needs_Action folder")
    print()

    print("IMPORTANT: Expose Your Webhook to the Internet")
    print("-" * 40)
    print()
    print("Meta requires HTTPS webhooks. For local development:")
    print()
    print("Option A: Use ngrok")
    print("  ngrok http 8000")
    print("  Then use the ngrok HTTPS URL as your Callback URL")
    print()
    print("Option B: Use cloudflared tunnel")
    print("  cloudflared tunnel --url http://localhost:8000")
    print()
    print("Option C: Deploy to a server with HTTPS")
    print()

    print("Environment Variables Summary")
    print("-" * 40)
    print()
    print("Required in .env:")
    print()
    print("  # Webhook verification token (shared secret with Meta)")
    print(f"  WHATSAPP_VERIFY_TOKEN={config['verify_token'] or 'your_verify_token'}")
    print()
    print("  # App secret for signature validation (from Meta Developer Console)")
    print(f"  WHATSAPP_APP_SECRET={config['app_secret'] or 'your_app_secret'}")
    print()
    print("Optional:")
    print()
    print("  # Webhook server configuration")
    print(f"  WEBHOOK_HOST={config['host']}")
    print(f"  WEBHOOK_PORT={config['port']}")
    print(f"  WEBHOOK_PUBLIC_URL={config['public_url']}")
    print()
    print("=" * 70)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Set up WhatsApp Business API webhook for AI Employee"
    )
    parser.add_argument(
        "--generate-token",
        action="store_true",
        help="Generate a new webhook verify token and save to .env"
    )
    parser.add_argument(
        "--test-signature",
        action="store_true",
        help="Test webhook signature validation"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output configuration as JSON"
    )
    parser.add_argument(
        "--set-secret",
        type=str,
        help="Set the app secret in .env"
    )
    args = parser.parse_args()

    # Get current configuration
    config = get_webhook_config()

    # Generate new token if requested
    if args.generate_token:
        new_token = generate_verify_token()
        logger.info(f"Generated new verify token: {new_token}")

        env_path = update_env_file(verify_token=new_token)
        logger.info(f"Updated {env_path}")

        # Refresh config
        os.environ["WHATSAPP_VERIFY_TOKEN"] = new_token
        config = get_webhook_config()

    # Set app secret if provided
    if args.set_secret:
        env_path = update_env_file(app_secret=args.set_secret)
        logger.info(f"Updated app secret in {env_path}")

        os.environ["WHATSAPP_APP_SECRET"] = args.set_secret
        config = get_webhook_config()

    # Test signature validation if requested
    if args.test_signature:
        print()
        print("Testing Webhook Signature Validation")
        print("-" * 40)

        if test_signature_validation(config['app_secret']):
            print()
            print("Signature validation is working correctly!")
            sys.exit(0)
        else:
            print()
            print("Signature validation test FAILED.")
            print("Please check your WHATSAPP_APP_SECRET configuration.")
            sys.exit(1)

    # Print setup instructions
    print_setup_instructions(config, json_output=args.json)


if __name__ == "__main__":
    main()
