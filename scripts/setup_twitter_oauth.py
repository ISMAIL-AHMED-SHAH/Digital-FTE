#!/usr/bin/env python3
"""Twitter OAuth Setup Script (T058).

Guides users through Twitter API v2 OAuth setup for the AI Employee.

Steps:
1. Verify Twitter App configuration
2. Generate OAuth 1.0a credentials
3. Test API connection
4. Store credentials securely

Usage:
    python scripts/setup_twitter_oauth.py --interactive
    python scripts/setup_twitter_oauth.py --verify
    python scripts/setup_twitter_oauth.py --test-tweet "Hello, testing!"
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    import httpx
except ImportError:
    print("Error: httpx is required. Install with: pip install httpx")
    sys.exit(1)

try:
    from requests_oauthlib import OAuth1
except ImportError:
    OAuth1 = None

# Twitter API endpoints
TWITTER_API_BASE = "https://api.twitter.com/2"
TWITTER_REQUEST_TOKEN_URL = "https://api.twitter.com/oauth/request_token"
TWITTER_AUTHORIZE_URL = "https://api.twitter.com/oauth/authorize"
TWITTER_ACCESS_TOKEN_URL = "https://api.twitter.com/oauth/access_token"


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
    """Get Twitter app configuration from environment."""
    return {
        "api_key": os.environ.get("TWITTER_API_KEY"),
        "api_secret": os.environ.get("TWITTER_API_SECRET"),
        "access_token": os.environ.get("TWITTER_ACCESS_TOKEN"),
        "access_secret": os.environ.get("TWITTER_ACCESS_SECRET"),
        "bearer_token": os.environ.get("TWITTER_BEARER_TOKEN"),
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
    prefix = {"info": "i", "success": "+", "warning": "!", "error": "x"}
    print(f"{colors.get(status, '')}[{prefix.get(status, '')}] {message}{reset}")


def verify_app_config():
    """Verify Twitter App configuration."""
    config = get_config()

    print("\n=== Twitter App Configuration ===\n")

    missing = []
    if not config["api_key"]:
        missing.append("TWITTER_API_KEY")
    if not config["api_secret"]:
        missing.append("TWITTER_API_SECRET")

    if missing:
        print_status(f"Missing required credentials: {', '.join(missing)}", "error")
        print("\nTo get these credentials:")
        print("1. Go to https://developer.twitter.com/en/portal/projects-and-apps")
        print("2. Create or select your app")
        print("3. Go to 'Keys and tokens' tab")
        print("4. Copy API Key and API Key Secret to config/.env")
        return False

    print_status(f"API Key: {config['api_key'][:10]}...", "success")

    # Check for access tokens
    if config["access_token"] and config["access_secret"]:
        print_status("Access Token: Configured", "success")
    else:
        print_status("Access Token: Not configured (run --interactive)", "warning")

    # Check for bearer token
    if config["bearer_token"]:
        print_status("Bearer Token: Configured", "success")
    else:
        print_status("Bearer Token: Not configured (optional)", "info")

    return True


def test_connection():
    """Test Twitter API connection."""
    config = get_config()

    if not all([config["api_key"], config["api_secret"],
                config["access_token"], config["access_secret"]]):
        print_status("Cannot test connection - missing credentials", "error")
        return False

    print("\n=== Testing Twitter API Connection ===\n")

    try:
        # Use Bearer token if available for simple test
        if config["bearer_token"]:
            headers = {"Authorization": f"Bearer {config['bearer_token']}"}
            response = httpx.get(
                f"{TWITTER_API_BASE}/users/me",
                headers=headers,
                timeout=10,
            )
        else:
            # Would need OAuth1 for this
            print_status("Bearer token recommended for connection test", "info")
            print_status("Skipping API test - configure TWITTER_BEARER_TOKEN for full test", "warning")
            return True

        if response.status_code == 200:
            data = response.json()
            user = data.get("data", {})
            print_status(f"Connected as: @{user.get('username', 'unknown')}", "success")
            print_status(f"User ID: {user.get('id', 'unknown')}", "info")
            return True
        else:
            print_status(f"API error: {response.status_code}", "error")
            print(response.text)
            return False

    except Exception as e:
        print_status(f"Connection failed: {e}", "error")
        return False


def test_tweet(text: str):
    """Test posting a tweet (dry run by default)."""
    config = get_config()

    if not all([config["api_key"], config["api_secret"],
                config["access_token"], config["access_secret"]]):
        print_status("Cannot post - missing credentials", "error")
        return False

    # Validate tweet length
    if len(text) > 280:
        print_status(f"Tweet too long: {len(text)}/280 characters", "error")
        return False

    print(f"\nTweet content ({len(text)}/280 chars):")
    print(f"  {text}")
    print()

    # Confirm before posting
    confirm = input("Post this tweet? (yes/no): ").strip().lower()
    if confirm != "yes":
        print_status("Tweet not posted", "info")
        return False

    # Would post here using twitter-api-v2 library
    print_status("Tweet posting requires twitter-api-v2 library", "warning")
    print("Install: npm install twitter-api-v2")
    print("Or use the MCP server through Claude")

    return True


def interactive_setup():
    """Run interactive OAuth setup."""
    print("\n" + "=" * 50)
    print("  Twitter OAuth Setup for AI Employee")
    print("=" * 50 + "\n")

    # Step 1: Verify configuration
    print_status("Step 1: Verifying app configuration...", "info")
    if not verify_app_config():
        return

    config = get_config()

    # Step 2: Check if access tokens exist
    if config["access_token"] and config["access_secret"]:
        print_status("\nAccess tokens already configured.", "success")
        test = input("Test the connection? (y/n): ").strip().lower()
        if test == "y":
            test_connection()
        return

    # Step 3: Guide through OAuth flow
    print_status("\nStep 2: OAuth 1.0a Setup", "info")
    print("\nTwitter uses OAuth 1.0a for user authentication.")
    print("This requires a 3-legged OAuth flow:\n")
    print("1. Get a request token from Twitter")
    print("2. User authorizes the app via browser")
    print("3. Exchange for access token\n")

    print("For automated setup, you'll need to:")
    print("1. Go to your Twitter Developer Portal")
    print("2. Navigate to your app's 'Keys and tokens'")
    print("3. Generate 'Access Token and Secret'")
    print("4. Add them to your config/.env file:\n")
    print("   TWITTER_ACCESS_TOKEN=your_access_token")
    print("   TWITTER_ACCESS_SECRET=your_access_token_secret")

    print("\n" + "-" * 50)
    print("\nAlternatively, for programmatic access:")
    print("1. Set up a callback URL in your app settings")
    print("2. Use the OAuth flow to get user authorization")
    print("3. Store the resulting tokens securely")

    # Prompt for manual entry
    print("\n" + "=" * 50)
    print("\nEnter your tokens (or press Enter to skip):")

    access_token = input("Access Token: ").strip()
    access_secret = input("Access Token Secret: ").strip()

    if access_token and access_secret:
        # Save to credentials file
        creds_dir = Path(__file__).parent.parent / "config" / "credentials"
        creds_dir.mkdir(parents=True, exist_ok=True)
        creds_file = creds_dir / "twitter_oauth.json"

        credentials = {
            "access_token": access_token,
            "access_token_secret": access_secret,
            "created_at": datetime.now().isoformat(),
        }

        with open(creds_file, "w") as f:
            json.dump(credentials, f, indent=2)

        os.chmod(creds_file, 0o600)
        print_status(f"Credentials saved to {creds_file}", "success")

        print("\nAdd these to your config/.env file:")
        print(f"TWITTER_ACCESS_TOKEN={access_token}")
        print(f"TWITTER_ACCESS_SECRET={access_secret}")
    else:
        print_status("No tokens entered. Setup incomplete.", "warning")


def show_rate_limits():
    """Show current rate limit status."""
    config = get_config()

    if not config["bearer_token"]:
        print_status("Bearer token required for rate limit check", "error")
        return

    print("\n=== Twitter Rate Limits ===\n")
    print("Twitter API v2 rate limits (per 15-min window):")
    print("  - Tweet creation: 300 tweets / 3 hours")
    print("  - User lookup: 900 requests")
    print("  - Tweet lookup: 900 requests")
    print("  - Search: 450 requests")
    print("\nNote: Rate limits vary by app tier and endpoint.")
    print("See: https://developer.twitter.com/en/docs/twitter-api/rate-limits")


def main():
    parser = argparse.ArgumentParser(
        description="Twitter OAuth Setup for AI Employee",
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
        help="Verify current credentials",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test API connection",
    )
    parser.add_argument(
        "--test-tweet",
        type=str,
        help="Test posting a tweet",
    )
    parser.add_argument(
        "--rate-limits",
        action="store_true",
        help="Show rate limit information",
    )

    args = parser.parse_args()

    # Load environment
    load_env()

    if args.interactive:
        interactive_setup()
    elif args.verify:
        verify_app_config()
    elif args.test:
        verify_app_config()
        test_connection()
    elif args.test_tweet:
        test_tweet(args.test_tweet)
    elif args.rate_limits:
        show_rate_limits()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
