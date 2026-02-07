#!/usr/bin/env python3
"""Meta OAuth Setup Script (T048).

Guides users through Facebook/Instagram OAuth setup for the AI Employee.

Steps:
1. Verify Meta App configuration
2. Generate login URL for user authorization
3. Exchange code for access token
4. Exchange for long-lived token
5. Get Page and Instagram Account IDs
6. Store credentials securely

Usage:
    python scripts/setup_meta_oauth.py --interactive
    python scripts/setup_meta_oauth.py --verify
    python scripts/setup_meta_oauth.py --refresh
"""

import argparse
import json
import os
import sys
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode, parse_qs, urlparse

try:
    import httpx
except ImportError:
    print("Error: httpx is required. Install with: pip install httpx")
    sys.exit(1)

# Meta OAuth endpoints
OAUTH_URL = "https://www.facebook.com/v18.0/dialog/oauth"
TOKEN_URL = "https://graph.facebook.com/v18.0/oauth/access_token"
DEBUG_TOKEN_URL = "https://graph.facebook.com/v18.0/debug_token"
GRAPH_API_BASE = "https://graph.facebook.com/v18.0"

# Required permissions for AI Employee
REQUIRED_PERMISSIONS = [
    "pages_show_list",
    "pages_read_engagement",
    "pages_manage_posts",
    "instagram_basic",
    "instagram_content_publish",
]


def load_env():
    """Load environment variables from .env file."""
    env_path = Path(__file__).parent.parent / "config" / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())


def get_config():
    """Get Meta app configuration from environment."""
    return {
        "app_id": os.environ.get("META_APP_ID"),
        "app_secret": os.environ.get("META_APP_SECRET"),
        "redirect_uri": os.environ.get("META_REDIRECT_URI", "https://localhost:8443/callback"),
    }


def print_status(message: str, status: str = "info"):
    """Print status message with color."""
    colors = {
        "info": "\033[94m",
        "success": "\033[92m",
        "warning": "\033[93m",
        "error": "\033[91m",
    }
    reset = "\033[0m"
    prefix = {"info": "ℹ", "success": "✓", "warning": "⚠", "error": "✗"}
    print(f"{colors.get(status, '')}{prefix.get(status, '')} {message}{reset}")


def verify_app_config():
    """Verify Meta App configuration."""
    config = get_config()

    print("\n=== Meta App Configuration ===\n")

    if not config["app_id"]:
        print_status("META_APP_ID not set", "error")
        print("  Set in config/.env or environment")
        return False

    if not config["app_secret"]:
        print_status("META_APP_SECRET not set", "error")
        print("  Set in config/.env or environment")
        return False

    print_status(f"App ID: {config['app_id']}", "success")
    print_status(f"Redirect URI: {config['redirect_uri']}", "info")

    return True


def generate_login_url():
    """Generate Facebook login URL for user authorization."""
    config = get_config()

    params = {
        "client_id": config["app_id"],
        "redirect_uri": config["redirect_uri"],
        "scope": ",".join(REQUIRED_PERMISSIONS),
        "response_type": "code",
        "state": "ai_employee_setup",
    }

    return f"{OAUTH_URL}?{urlencode(params)}"


def exchange_code_for_token(code: str) -> dict | None:
    """Exchange authorization code for access token."""
    config = get_config()

    try:
        response = httpx.get(
            TOKEN_URL,
            params={
                "client_id": config["app_id"],
                "redirect_uri": config["redirect_uri"],
                "client_secret": config["app_secret"],
                "code": code,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        print_status(f"Failed to exchange code: {e}", "error")
        return None


def exchange_for_long_lived_token(short_lived_token: str) -> dict | None:
    """Exchange short-lived token for long-lived token."""
    config = get_config()

    try:
        response = httpx.get(
            TOKEN_URL,
            params={
                "grant_type": "fb_exchange_token",
                "client_id": config["app_id"],
                "client_secret": config["app_secret"],
                "fb_exchange_token": short_lived_token,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        print_status(f"Failed to exchange for long-lived token: {e}", "error")
        return None


def debug_token(access_token: str) -> dict | None:
    """Debug/inspect access token."""
    config = get_config()
    app_token = f"{config['app_id']}|{config['app_secret']}"

    try:
        response = httpx.get(
            DEBUG_TOKEN_URL,
            params={
                "input_token": access_token,
                "access_token": app_token,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json().get("data", {})
    except httpx.HTTPError as e:
        print_status(f"Failed to debug token: {e}", "error")
        return None


def get_user_pages(access_token: str) -> list:
    """Get list of Facebook Pages the user manages."""
    try:
        response = httpx.get(
            f"{GRAPH_API_BASE}/me/accounts",
            params={
                "access_token": access_token,
                "fields": "id,name,access_token,instagram_business_account",
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json().get("data", [])
    except httpx.HTTPError as e:
        print_status(f"Failed to get pages: {e}", "error")
        return []


def interactive_setup():
    """Run interactive OAuth setup."""
    print("\n" + "=" * 50)
    print("  Meta OAuth Setup for AI Employee")
    print("=" * 50 + "\n")

    # Step 1: Verify configuration
    print_status("Step 1: Verifying app configuration...", "info")
    if not verify_app_config():
        print("\nPlease configure your Meta App credentials first.")
        print("1. Go to https://developers.facebook.com/apps")
        print("2. Create or select your app")
        print("3. Copy App ID and App Secret to config/.env")
        return

    print_status("App configuration verified", "success")

    # Step 2: Generate login URL
    print_status("\nStep 2: Generating login URL...", "info")
    login_url = generate_login_url()
    print(f"\nAuthorization URL:\n{login_url}\n")

    open_browser = input("Open in browser? (y/n): ").strip().lower()
    if open_browser == "y":
        webbrowser.open(login_url)

    # Step 3: Get authorization code
    print_status("\nStep 3: Waiting for authorization...", "info")
    print("After authorizing, you'll be redirected to a URL like:")
    print("  https://localhost:8443/callback?code=XXXXX&state=ai_employee_setup")
    print("\nPaste the FULL redirect URL here:")

    redirect_url = input("> ").strip()

    # Parse the code from the URL
    parsed = urlparse(redirect_url)
    params = parse_qs(parsed.query)
    code = params.get("code", [None])[0]

    if not code:
        print_status("Could not extract authorization code from URL", "error")
        return

    print_status("Authorization code received", "success")

    # Step 4: Exchange for access token
    print_status("\nStep 4: Exchanging code for access token...", "info")
    token_response = exchange_code_for_token(code)

    if not token_response or "access_token" not in token_response:
        print_status("Failed to get access token", "error")
        return

    short_lived_token = token_response["access_token"]
    print_status("Short-lived token obtained", "success")

    # Step 5: Exchange for long-lived token
    print_status("\nStep 5: Exchanging for long-lived token...", "info")
    long_lived_response = exchange_for_long_lived_token(short_lived_token)

    if not long_lived_response or "access_token" not in long_lived_response:
        print_status("Failed to get long-lived token", "error")
        return

    long_lived_token = long_lived_response["access_token"]
    expires_in = long_lived_response.get("expires_in", 0)
    expires_at = datetime.now() + timedelta(seconds=expires_in)

    print_status(f"Long-lived token obtained (expires: {expires_at.strftime('%Y-%m-%d')})", "success")

    # Step 6: Get Pages and Instagram accounts
    print_status("\nStep 6: Fetching your Pages and Instagram accounts...", "info")
    pages = get_user_pages(long_lived_token)

    if not pages:
        print_status("No Pages found. Make sure you have admin access to at least one Page.", "warning")
    else:
        print(f"\nFound {len(pages)} Page(s):\n")
        for i, page in enumerate(pages, 1):
            print(f"  {i}. {page['name']}")
            print(f"     Page ID: {page['id']}")
            if page.get("instagram_business_account"):
                print(f"     Instagram ID: {page['instagram_business_account']['id']}")
            print()

    # Step 7: Save credentials
    print_status("\nStep 7: Saving credentials...", "info")

    credentials = {
        "access_token": long_lived_token,
        "token_type": "bearer",
        "expires_at": expires_at.isoformat(),
        "pages": [
            {
                "id": page["id"],
                "name": page["name"],
                "access_token": page.get("access_token"),
                "instagram_account_id": page.get("instagram_business_account", {}).get("id"),
            }
            for page in pages
        ],
        "created_at": datetime.now().isoformat(),
    }

    # Save to secure location
    creds_dir = Path(__file__).parent.parent / "config" / "credentials"
    creds_dir.mkdir(parents=True, exist_ok=True)
    creds_file = creds_dir / "meta_oauth.json"

    with open(creds_file, "w") as f:
        json.dump(credentials, f, indent=2)

    # Set restrictive permissions
    os.chmod(creds_file, 0o600)

    print_status(f"Credentials saved to {creds_file}", "success")

    # Print environment variable hints
    print("\n" + "=" * 50)
    print("  Setup Complete!")
    print("=" * 50)
    print("\nAdd these to your config/.env file:")
    print(f"\nMETA_ACCESS_TOKEN={long_lived_token}")
    if pages:
        print(f"META_PAGE_ID={pages[0]['id']}")
        if pages[0].get("instagram_business_account"):
            print(f"META_INSTAGRAM_ID={pages[0]['instagram_business_account']['id']}")

    print("\n⚠️  Remember to keep your tokens secure!")
    print("   - Never commit tokens to version control")
    print("   - Rotate tokens if they may have been exposed")


def verify_token():
    """Verify current access token."""
    print("\n=== Token Verification ===\n")

    access_token = os.environ.get("META_ACCESS_TOKEN")
    if not access_token:
        print_status("META_ACCESS_TOKEN not set", "error")
        return

    token_info = debug_token(access_token)
    if not token_info:
        return

    print_status(f"Token Valid: {token_info.get('is_valid', False)}",
                "success" if token_info.get("is_valid") else "error")

    if token_info.get("expires_at"):
        expires = datetime.fromtimestamp(token_info["expires_at"])
        days_left = (expires - datetime.now()).days
        print_status(f"Expires: {expires.strftime('%Y-%m-%d')} ({days_left} days)",
                    "success" if days_left > 7 else "warning")

    if token_info.get("scopes"):
        print_status(f"Scopes: {', '.join(token_info['scopes'])}", "info")

    # Check for missing permissions
    missing = set(REQUIRED_PERMISSIONS) - set(token_info.get("scopes", []))
    if missing:
        print_status(f"Missing permissions: {', '.join(missing)}", "warning")


def refresh_token():
    """Refresh the current access token."""
    print("\n=== Token Refresh ===\n")

    access_token = os.environ.get("META_ACCESS_TOKEN")
    if not access_token:
        print_status("META_ACCESS_TOKEN not set", "error")
        return

    # First verify the current token
    token_info = debug_token(access_token)
    if not token_info or not token_info.get("is_valid"):
        print_status("Current token is invalid. Run --interactive to re-authorize.", "error")
        return

    # Exchange for new long-lived token
    print_status("Refreshing token...", "info")
    new_token_response = exchange_for_long_lived_token(access_token)

    if not new_token_response or "access_token" not in new_token_response:
        print_status("Failed to refresh token", "error")
        return

    new_token = new_token_response["access_token"]
    expires_in = new_token_response.get("expires_in", 0)
    expires_at = datetime.now() + timedelta(seconds=expires_in)

    print_status(f"Token refreshed (expires: {expires_at.strftime('%Y-%m-%d')})", "success")
    print(f"\nNew token:\nMETA_ACCESS_TOKEN={new_token}")


def main():
    parser = argparse.ArgumentParser(
        description="Meta OAuth Setup for AI Employee",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run interactive OAuth setup",
    )
    parser.add_argument(
        "--verify", "-v",
        action="store_true",
        help="Verify current access token",
    )
    parser.add_argument(
        "--refresh", "-r",
        action="store_true",
        help="Refresh the current access token",
    )

    args = parser.parse_args()

    # Load environment
    load_env()

    if args.interactive:
        interactive_setup()
    elif args.verify:
        verify_token()
    elif args.refresh:
        refresh_token()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
