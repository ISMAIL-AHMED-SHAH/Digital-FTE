#!/usr/bin/env python3
"""Odoo Connection Setup Script (T026).

Tests Odoo connectivity and helps configure API credentials.

Usage:
    python scripts/setup_odoo_connection.py --url https://odoo.example.com --db mydb --user admin

Environment variables:
    ODOO_URL: Odoo server URL
    ODOO_DATABASE: Database name
    ODOO_USERNAME: Username
    ODOO_PASSWORD: Password (or use --api-key)
    ODOO_API_KEY: API key (recommended over password)
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import requests
except ImportError:
    print("Error: requests library required. Install with: pip install requests")
    sys.exit(1)


class OdooConnectionTester:
    """Test Odoo connection and API access."""

    def __init__(self, url: str, database: str, username: str, password: str = None, api_key: str = None):
        self.url = url.rstrip("/")
        self.database = database
        self.username = username
        self.password = password or api_key or ""
        self.uid = None
        self.timeout = 30

    def _jsonrpc(self, service: str, method: str, args: list) -> dict:
        """Execute JSON-RPC call."""
        endpoint = urljoin(self.url, "/jsonrpc")
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": service,
                "method": method,
                "args": args,
            },
            "id": int(time.time() * 1000),
        }

        response = requests.post(
            endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()

        result = response.json()
        if "error" in result:
            raise Exception(f"Odoo error: {result['error']}")

        return result.get("result")

    def test_connectivity(self) -> dict:
        """Test basic connectivity to Odoo server."""
        print(f"Testing connectivity to {self.url}...")

        start = time.time()
        try:
            version = self._jsonrpc("common", "version", [])
            latency = int((time.time() - start) * 1000)

            print(f"  ✓ Connected in {latency}ms")
            print(f"  ✓ Odoo version: {version.get('server_version', 'unknown')}")

            return {
                "success": True,
                "version": version.get("server_version"),
                "latency_ms": latency,
            }
        except requests.exceptions.ConnectionError as e:
            print(f"  ✗ Connection failed: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            print(f"  ✗ Error: {e}")
            return {"success": False, "error": str(e)}

    def test_authentication(self) -> dict:
        """Test authentication with provided credentials."""
        print(f"Testing authentication as {self.username}...")

        try:
            self.uid = self._jsonrpc(
                "common",
                "authenticate",
                [self.database, self.username, self.password, {}],
            )

            if self.uid:
                print(f"  ✓ Authenticated (UID: {self.uid})")

                # Get user info
                user_info = self._jsonrpc(
                    "object",
                    "execute_kw",
                    [
                        self.database,
                        self.uid,
                        self.password,
                        "res.users",
                        "search_read",
                        [[["id", "=", self.uid]]],
                        {"fields": ["name", "company_id"]},
                    ],
                )

                if user_info:
                    user = user_info[0]
                    print(f"  ✓ User: {user.get('name')}")
                    print(f"  ✓ Company: {user.get('company_id', [None, 'Unknown'])[1]}")

                return {
                    "success": True,
                    "uid": self.uid,
                    "user": user_info[0] if user_info else None,
                }
            else:
                print("  ✗ Authentication failed - invalid credentials")
                return {"success": False, "error": "Invalid credentials"}

        except Exception as e:
            print(f"  ✗ Authentication error: {e}")
            return {"success": False, "error": str(e)}

    def test_accounting_access(self) -> dict:
        """Test access to accounting models."""
        if not self.uid:
            return {"success": False, "error": "Not authenticated"}

        print("Testing accounting module access...")

        models_to_check = [
            ("account.move", "Invoices"),
            ("account.payment", "Payments"),
            ("res.partner", "Partners"),
            ("account.journal", "Journals"),
        ]

        results = {}
        for model, label in models_to_check:
            try:
                # Try to read one record
                records = self._jsonrpc(
                    "object",
                    "execute_kw",
                    [
                        self.database,
                        self.uid,
                        self.password,
                        model,
                        "search_read",
                        [[]],
                        {"limit": 1, "fields": ["id"]},
                    ],
                )
                results[model] = {"accessible": True, "count": len(records)}
                print(f"  ✓ {label} ({model}): accessible")
            except Exception as e:
                results[model] = {"accessible": False, "error": str(e)}
                print(f"  ✗ {label} ({model}): {e}")

        success = all(r.get("accessible") for r in results.values())
        return {"success": success, "models": results}

    def run_full_test(self) -> dict:
        """Run complete connection test suite."""
        print("\n" + "=" * 60)
        print("Odoo Connection Test")
        print("=" * 60 + "\n")

        results = {
            "url": self.url,
            "database": self.database,
            "username": self.username,
        }

        # Test connectivity
        connectivity = self.test_connectivity()
        results["connectivity"] = connectivity
        if not connectivity["success"]:
            results["overall_success"] = False
            return results

        print()

        # Test authentication
        auth = self.test_authentication()
        results["authentication"] = auth
        if not auth["success"]:
            results["overall_success"] = False
            return results

        print()

        # Test accounting access
        accounting = self.test_accounting_access()
        results["accounting_access"] = accounting

        print()

        # Summary
        results["overall_success"] = all([
            connectivity["success"],
            auth["success"],
            accounting["success"],
        ])

        if results["overall_success"]:
            print("=" * 60)
            print("✓ All tests passed! Odoo connection is ready.")
            print("=" * 60)
        else:
            print("=" * 60)
            print("✗ Some tests failed. Check the results above.")
            print("=" * 60)

        return results


def save_credentials_hint(url: str, database: str, username: str):
    """Print hint for saving credentials."""
    print("\n" + "-" * 60)
    print("To save credentials, add to your .env file:")
    print("-" * 60)
    print(f"ODOO_URL={url}")
    print(f"ODOO_DATABASE={database}")
    print(f"ODOO_USERNAME={username}")
    print("ODOO_API_KEY=your_api_key_here")
    print("-" * 60)
    print("\nTo generate an API key in Odoo:")
    print("1. Go to Settings > Users & Companies > Users")
    print("2. Select your user")
    print("3. Go to 'Account Security' tab")
    print("4. Click 'New API Key'")
    print("5. Copy the generated key")
    print("-" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Test Odoo connection and configure credentials"
    )
    parser.add_argument(
        "--url",
        default=os.environ.get("ODOO_URL"),
        help="Odoo server URL (or set ODOO_URL env var)",
    )
    parser.add_argument(
        "--db", "--database",
        default=os.environ.get("ODOO_DATABASE"),
        help="Database name (or set ODOO_DATABASE env var)",
    )
    parser.add_argument(
        "--user", "--username",
        default=os.environ.get("ODOO_USERNAME"),
        help="Username (or set ODOO_USERNAME env var)",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("ODOO_PASSWORD"),
        help="Password (or set ODOO_PASSWORD env var)",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("ODOO_API_KEY"),
        help="API key (recommended, or set ODOO_API_KEY env var)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    # Validate required args
    if not args.url:
        parser.error("Odoo URL required (--url or ODOO_URL env var)")
    if not args.db:
        parser.error("Database name required (--db or ODOO_DATABASE env var)")
    if not args.user:
        parser.error("Username required (--user or ODOO_USERNAME env var)")
    if not args.password and not args.api_key:
        parser.error("Password or API key required (--password/--api-key or env var)")

    # Run tests
    tester = OdooConnectionTester(
        url=args.url,
        database=args.db,
        username=args.user,
        password=args.password,
        api_key=args.api_key,
    )

    results = tester.run_full_test()

    if args.json:
        print("\n" + json.dumps(results, indent=2))
    elif results["overall_success"]:
        save_credentials_hint(args.url, args.db, args.user)

    sys.exit(0 if results["overall_success"] else 1)


if __name__ == "__main__":
    main()
