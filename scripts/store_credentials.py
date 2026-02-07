#!/usr/bin/env python3
"""Credential Storage Utility for AI Employee.

Helper script to manually store OAuth tokens/credentials in the 
secure credential manager (keyring or encrypted file).

Usage:
    python scripts/store_credentials.py --service linkedin
"""

import argparse
import getpass
import json
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.common.credentials import get_credential_manager

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Store credentials for AI Employee services")
    parser.add_argument(
        "--service", 
        required=True, 
        choices=["linkedin", "gmail", "whatsapp"],
        help="Service to store credentials for"
    )
    args = parser.parse_args()

    print(f"\n=== Setup Credentials for {args.service.upper()} ===\n")
    print("This script will store your credentials securely in the OS keychain")
    print("or an encrypted local file.\n")

    data = {}

    if args.service == "linkedin":
        print("Please enter your LinkedIn API credentials:")
        print("(Get these from https://www.linkedin.com/developers/apps)\n")
        
        data["client_id"] = input("Client ID: ").strip()
        data["client_secret"] = getpass.getpass("Client Secret: ").strip()
        data["access_token"] = getpass.getpass("Access Token: ").strip()
        data["refresh_token"] = getpass.getpass("Refresh Token (optional, press Enter to skip): ").strip()
        
        if not data["refresh_token"]:
            del data["refresh_token"]

    elif args.service == "whatsapp":
        print("Please enter your WhatsApp Business API credentials:")
        print("(Get these from https://developers.facebook.com/apps)\n")
        
        data["access_token"] = getpass.getpass("System User Access Token: ").strip()
        data["phone_number_id"] = input("Phone Number ID: ").strip()
        data["business_account_id"] = input("Business Account ID: ").strip()
        data["app_secret"] = getpass.getpass("App Secret: ").strip()

    elif args.service == "gmail":
        print("NOTE: For Gmail, it is recommended to use 'scripts/setup_gmail_oauth.py'")
        print("instead, as it handles the full OAuth flow.\n")
        confirm = input("Continue with manual entry? (y/n): ").lower()
        if confirm != 'y':
            return

        data["client_id"] = input("Client ID: ").strip()
        data["client_secret"] = getpass.getpass("Client Secret: ").strip()
        data["access_token"] = getpass.getpass("Access Token: ").strip()
        data["refresh_token"] = getpass.getpass("Refresh Token: ").strip()

    # Store
    try:
        manager = get_credential_manager()
        manager.store_token(args.service, data)
        print(f"\n✅ Successfully stored credentials for {args.service}!")
        print("You can now run the associated watcher or MCP server.")
        
    except Exception as e:
        print(f"\n❌ Failed to store credentials: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
