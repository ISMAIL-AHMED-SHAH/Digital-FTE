#!/usr/bin/env python3
"""Gmail OAuth2 Setup Script for Silver Tier.

This script runs the OAuth2 authorization flow for Gmail API access
and stores the tokens in the OS credential manager.

Prerequisites:
1. Create a Google Cloud project at https://console.cloud.google.com
2. Enable the Gmail API
3. Create OAuth 2.0 credentials (Desktop application)
4. Download the credentials JSON file
5. Set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET in .env or provide credentials file

Usage:
    python scripts/setup_gmail_oauth.py

    # With credentials file
    python scripts/setup_gmail_oauth.py --credentials-file path/to/credentials.json

    # Test mode (verify existing credentials)
    python scripts/setup_gmail_oauth.py --test
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

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

# Gmail API scopes
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify"
]


def get_credentials_from_env() -> tuple[str, str] | None:
    """Get client credentials from environment variables.

    Returns:
        Tuple of (client_id, client_secret) or None if not set
    """
    client_id = os.environ.get("GMAIL_CLIENT_ID")
    client_secret = os.environ.get("GMAIL_CLIENT_SECRET")

    if client_id and client_secret:
        return client_id, client_secret

    return None


def get_credentials_from_file(file_path: str) -> tuple[str, str]:
    """Get client credentials from Google credentials JSON file.

    Args:
        file_path: Path to credentials.json downloaded from Google Cloud Console

    Returns:
        Tuple of (client_id, client_secret)

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Credentials file not found: {file_path}")

    with open(path, "r") as f:
        data = json.load(f)

    # Handle both "installed" and "web" credential types
    if "installed" in data:
        creds = data["installed"]
    elif "web" in data:
        creds = data["web"]
    else:
        raise ValueError("Invalid credentials file format. Expected 'installed' or 'web' key.")

    client_id = creds.get("client_id")
    client_secret = creds.get("client_secret")

    if not client_id or not client_secret:
        raise ValueError("Credentials file missing client_id or client_secret")

    return client_id, client_secret


def run_oauth_flow(client_id: str, client_secret: str) -> dict:
    """Run the OAuth2 authorization flow.

    Opens a browser for user authentication and returns the tokens.

    Args:
        client_id: Google OAuth client ID
        client_secret: Google OAuth client secret

    Returns:
        Dict with access_token, refresh_token, expires_at, client_id, client_secret
    """
    from google_auth_oauthlib.flow import InstalledAppFlow

    # Build client config
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"]
        }
    }

    # Run flow
    flow = InstalledAppFlow.from_client_config(client_config, GMAIL_SCOPES)

    logger.info("Opening browser for Gmail authorization...")
    logger.info("Please sign in and grant access to your Gmail account.")

    credentials = flow.run_local_server(port=0)

    logger.info("Authorization successful!")

    # Build token data
    token_data = {
        "access_token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "expires_at": credentials.expiry.isoformat() if credentials.expiry else None
    }

    return token_data


def store_tokens(token_data: dict) -> None:
    """Store tokens in the credential manager.

    Args:
        token_data: Dict with access_token, refresh_token, etc.
    """
    from src.common.credentials import get_credential_manager

    cred_manager = get_credential_manager()

    if not cred_manager.is_available():
        logger.error("No credential storage available!")
        logger.error("Please install 'keyring' package or ensure encryption is available.")
        sys.exit(1)

    cred_manager.store_token("gmail", token_data)
    logger.info("Tokens stored successfully in credential manager")


def test_credentials() -> bool:
    """Test that stored credentials work.

    Returns:
        True if credentials are valid
    """
    from src.common.credentials import get_credential_manager
    from src.watchers.gmail_client import GmailClient

    logger.info("Testing stored credentials...")

    cred_manager = get_credential_manager()
    token = cred_manager.get_token("gmail")

    if not token:
        logger.error("No stored credentials found")
        return False

    logger.info("Found stored credentials")

    # Try to authenticate
    try:
        client = GmailClient()
        client.authenticate()

        profile = client.get_profile()
        email = profile.get("emailAddress")

        logger.info(f"Successfully authenticated as: {email}")
        logger.info(f"Total messages: {profile.get('messagesTotal', 'unknown')}")

        return True

    except Exception as e:
        logger.error(f"Failed to authenticate: {e}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Set up Gmail OAuth2 credentials for AI Employee"
    )
    parser.add_argument(
        "--credentials-file",
        help="Path to Google OAuth credentials.json file"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test existing credentials instead of running OAuth flow"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-authentication even if credentials exist"
    )
    args = parser.parse_args()

    print()
    print("=" * 60)
    print("Gmail OAuth2 Setup for AI Employee")
    print("=" * 60)
    print()

    # Test mode
    if args.test:
        if test_credentials():
            print("\n✅ Gmail credentials are valid!")
            sys.exit(0)
        else:
            print("\n❌ Gmail credentials are invalid or missing.")
            print("Run this script without --test to set up credentials.")
            sys.exit(1)

    # Check for existing credentials
    if not args.force:
        from src.common.credentials import get_credential_manager
        cred_manager = get_credential_manager()

        if cred_manager.get_token("gmail"):
            logger.info("Existing credentials found. Use --force to re-authenticate.")
            if test_credentials():
                print("\n✅ Existing credentials are valid!")
                sys.exit(0)
            else:
                logger.info("Existing credentials are invalid, proceeding with new auth...")

    # Get client credentials
    if args.credentials_file:
        logger.info(f"Loading credentials from: {args.credentials_file}")
        try:
            client_id, client_secret = get_credentials_from_file(args.credentials_file)
        except Exception as e:
            logger.error(f"Failed to load credentials file: {e}")
            sys.exit(1)
    else:
        env_creds = get_credentials_from_env()
        if env_creds:
            logger.info("Using credentials from environment variables")
            client_id, client_secret = env_creds
        else:
            print("No credentials found!")
            print()
            print("Please provide credentials using one of these methods:")
            print()
            print("1. Set environment variables:")
            print("   GMAIL_CLIENT_ID=your_client_id")
            print("   GMAIL_CLIENT_SECRET=your_client_secret")
            print()
            print("2. Use a credentials file:")
            print("   python scripts/setup_gmail_oauth.py --credentials-file path/to/credentials.json")
            print()
            print("To get credentials:")
            print("1. Go to https://console.cloud.google.com")
            print("2. Create a project and enable Gmail API")
            print("3. Create OAuth 2.0 credentials (Desktop application)")
            print("4. Download the credentials JSON file")
            print()
            sys.exit(1)

    # Run OAuth flow
    try:
        token_data = run_oauth_flow(client_id, client_secret)
    except Exception as e:
        logger.error(f"OAuth flow failed: {e}")
        sys.exit(1)

    # Store tokens
    try:
        store_tokens(token_data)
    except Exception as e:
        logger.error(f"Failed to store tokens: {e}")
        sys.exit(1)

    # Verify
    if test_credentials():
        print()
        print("=" * 60)
        print("✅ Gmail OAuth2 setup complete!")
        print("=" * 60)
        print()
        print("You can now run the Gmail watcher:")
        print("  python -m src.watchers.gmail_watcher")
        print()
    else:
        print()
        print("⚠️ Setup completed but verification failed.")
        print("Please check the logs for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
