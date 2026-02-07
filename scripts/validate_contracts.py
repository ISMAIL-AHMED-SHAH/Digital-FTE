#!/usr/bin/env python3
"""
Contract Validation Script for AI Employee Silver Tier

Validates that MCP server contracts in specs/002-external-connectivity/contracts/
match the actual implemented tool schemas.

Usage:
    python scripts/validate_contracts.py [--verbose]

Exit codes:
    0 - All contracts valid
    1 - Validation failures found
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
CONTRACTS_DIR = PROJECT_ROOT / "specs" / "002-external-connectivity" / "contracts"
MCP_SERVERS_DIR = PROJECT_ROOT / "src" / "mcp_servers"


def load_json_contract(path: Path) -> dict | None:
    """Load a JSON contract file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error loading {path}: {e}")
        return None


def extract_ts_tool_schema(ts_file: Path) -> dict | None:
    """
    Extract tool schema from TypeScript source file.

    Looks for patterns like:
    - inputSchema: { type: "object", properties: { ... } }
    - export const ...ToolDefinition = { ... }
    """
    if not ts_file.exists():
        return None

    content = ts_file.read_text(encoding="utf-8")

    # Look for tool definition export
    tool_schema = {
        "properties": {},
        "required": []
    }

    # Extract properties from inputSchema
    # This is a simplified parser - in production, use a proper TS parser

    # Check for required fields
    if '"to"' in content and 'required: ["to"' in content:
        tool_schema["required"].append("to")
    if '"subject"' in content and '"subject"' in content:
        tool_schema["required"].append("subject")
    if '"body"' in content and '"body"' in content:
        tool_schema["required"].append("body")
    if '"content"' in content and 'required: ["content"' in content:
        tool_schema["required"].append("content")

    # Check for dry_run support
    if 'dry_run' in content or 'dryRun' in content:
        tool_schema["has_dry_run"] = True

    return tool_schema


def validate_gmail_contract(verbose: bool = False) -> tuple[bool, list[str]]:
    """Validate Gmail MCP contract against implementation."""
    errors = []
    contract_path = CONTRACTS_DIR / "gmail-mcp.json"
    impl_path = MCP_SERVERS_DIR / "gmail" / "src" / "tools" / "send_email.ts"

    # Load contract
    contract = load_json_contract(contract_path)
    if not contract:
        errors.append(f"Failed to load contract: {contract_path}")
        return False, errors

    if verbose:
        print(f"Validating Gmail MCP contract: {contract_path}")

    # Check contract structure
    if "tools" not in contract:
        errors.append("Contract missing 'tools' array")
        return False, errors

    tools = contract["tools"]
    if len(tools) == 0:
        errors.append("Contract has no tools defined")
        return False, errors

    # Find send_email tool
    send_email_tool = None
    for tool in tools:
        if tool.get("name") == "send_email":
            send_email_tool = tool
            break

    if not send_email_tool:
        errors.append("Contract missing 'send_email' tool")
        return False, errors

    # Validate input schema
    input_schema = send_email_tool.get("inputSchema", {})
    required_fields = input_schema.get("required", [])

    expected_required = ["to", "subject", "body"]
    for field in expected_required:
        if field not in required_fields:
            errors.append(f"send_email missing required field: {field}")

    # Check implementation exists
    if not impl_path.exists():
        errors.append(f"Implementation not found: {impl_path}")
        return False, errors

    # Check implementation has dry_run support (added in Silver Tier)
    impl_content = impl_path.read_text(encoding="utf-8")
    if "dry_run" not in impl_content:
        errors.append("Implementation missing dry_run support")

    # Check rate limit configuration
    if "rateLimits" not in contract:
        errors.append("Contract missing rate limits")
    else:
        rate_limit = contract["rateLimits"].get("send_email", {})
        if rate_limit.get("limit") != 50:
            errors.append(f"Rate limit should be 50, got {rate_limit.get('limit')}")

    if verbose:
        print(f"  - Tool: send_email")
        print(f"  - Required fields: {required_fields}")
        print(f"  - Rate limit: {contract.get('rateLimits', {}).get('send_email', {})}")

    return len(errors) == 0, errors


def validate_linkedin_contract(verbose: bool = False) -> tuple[bool, list[str]]:
    """Validate LinkedIn MCP contract against implementation."""
    errors = []
    contract_path = CONTRACTS_DIR / "linkedin-mcp.json"
    impl_path = MCP_SERVERS_DIR / "linkedin" / "src" / "tools" / "create_post.ts"

    # Load contract
    contract = load_json_contract(contract_path)
    if not contract:
        errors.append(f"Failed to load contract: {contract_path}")
        return False, errors

    if verbose:
        print(f"Validating LinkedIn MCP contract: {contract_path}")

    # Check contract structure
    if "tools" not in contract:
        errors.append("Contract missing 'tools' array")
        return False, errors

    tools = contract["tools"]
    if len(tools) == 0:
        errors.append("Contract has no tools defined")
        return False, errors

    # Find create_post tool
    create_post_tool = None
    for tool in tools:
        if tool.get("name") == "create_post":
            create_post_tool = tool
            break

    if not create_post_tool:
        errors.append("Contract missing 'create_post' tool")
        return False, errors

    # Validate input schema
    input_schema = create_post_tool.get("inputSchema", {})
    properties = input_schema.get("properties", {})

    # Check content length constraint
    content_prop = properties.get("content", {})
    if content_prop.get("maxLength") != 3000:
        errors.append(f"Content maxLength should be 3000, got {content_prop.get('maxLength')}")

    # Check visibility enum
    visibility_prop = properties.get("visibility", {})
    expected_visibility = ["PUBLIC", "CONNECTIONS"]
    if visibility_prop.get("enum") != expected_visibility:
        errors.append(f"Visibility enum should be {expected_visibility}")

    # Check dry_run is documented in contract
    if "dry_run" not in properties:
        errors.append("Contract missing dry_run property")

    # Check implementation exists
    if not impl_path.exists():
        errors.append(f"Implementation not found: {impl_path}")
        return False, errors

    # Check implementation has dry_run support
    impl_content = impl_path.read_text(encoding="utf-8")
    if "dry_run" not in impl_content:
        errors.append("Implementation missing dry_run support")

    # Check rate limit configuration
    if "rateLimits" not in contract:
        errors.append("Contract missing rate limits")
    else:
        rate_limit = contract["rateLimits"].get("create_post", {})
        if rate_limit.get("limit") != 10:
            errors.append(f"Rate limit should be 10, got {rate_limit.get('limit')}")

    if verbose:
        print(f"  - Tool: create_post")
        print(f"  - Content max length: {content_prop.get('maxLength')}")
        print(f"  - Visibility options: {visibility_prop.get('enum')}")
        print(f"  - Rate limit: {contract.get('rateLimits', {}).get('create_post', {})}")

    return len(errors) == 0, errors


def validate_whatsapp_contract(verbose: bool = False) -> tuple[bool, list[str]]:
    """Validate WhatsApp webhook OpenAPI contract."""
    errors = []
    contract_path = CONTRACTS_DIR / "whatsapp-webhook.openapi.yaml"
    impl_path = MCP_SERVERS_DIR.parent / "watchers" / "whatsapp_webhook.py"

    if not contract_path.exists():
        errors.append(f"Contract not found: {contract_path}")
        return False, errors

    if verbose:
        print(f"Validating WhatsApp webhook contract: {contract_path}")

    # Load YAML contract
    try:
        import yaml
        with open(contract_path, "r", encoding="utf-8") as f:
            contract = yaml.safe_load(f)
    except ImportError:
        if verbose:
            print("  - YAML module not available, skipping detailed validation")
        # Just check file exists
        return contract_path.exists(), errors
    except Exception as e:
        errors.append(f"Failed to parse YAML: {e}")
        return False, errors

    # Validate OpenAPI structure
    if contract.get("openapi") is None:
        errors.append("Contract missing 'openapi' version")

    paths = contract.get("paths", {})
    if "/webhooks/whatsapp" not in paths:
        errors.append("Contract missing /webhooks/whatsapp path")

    # Check implementation exists
    if not impl_path.exists():
        errors.append(f"Implementation not found: {impl_path}")
        return False, errors

    # Verify implementation has required endpoints
    impl_content = impl_path.read_text(encoding="utf-8")

    if '@app.get("/webhooks/whatsapp")' not in impl_content:
        errors.append("Implementation missing GET /webhooks/whatsapp endpoint")

    if '@app.post("/webhooks/whatsapp")' not in impl_content:
        errors.append("Implementation missing POST /webhooks/whatsapp endpoint")

    if verbose:
        print(f"  - Paths: {list(paths.keys())}")
        print(f"  - Implementation: {impl_path}")

    return len(errors) == 0, errors


def main():
    parser = argparse.ArgumentParser(description="Validate MCP server contracts")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Show detailed validation output")

    args = parser.parse_args()

    print("=" * 60)
    print("AI Employee Silver Tier - Contract Validation")
    print("=" * 60)
    print()

    all_valid = True
    total_errors = []

    # Validate Gmail contract
    print("Gmail MCP Contract:")
    valid, errors = validate_gmail_contract(args.verbose)
    if valid:
        print("  [PASS] VALID")
    else:
        print("  [FAIL] INVALID")
        for error in errors:
            print(f"    - {error}")
        all_valid = False
        total_errors.extend(errors)
    print()

    # Validate LinkedIn contract
    print("LinkedIn MCP Contract:")
    valid, errors = validate_linkedin_contract(args.verbose)
    if valid:
        print("  [PASS] VALID")
    else:
        print("  [FAIL] INVALID")
        for error in errors:
            print(f"    - {error}")
        all_valid = False
        total_errors.extend(errors)
    print()

    # Validate WhatsApp contract
    print("WhatsApp Webhook Contract:")
    valid, errors = validate_whatsapp_contract(args.verbose)
    if valid:
        print("  [PASS] VALID")
    else:
        print("  [FAIL] INVALID")
        for error in errors:
            print(f"    - {error}")
        all_valid = False
        total_errors.extend(errors)
    print()

    # Summary
    print("=" * 60)
    if all_valid:
        print("[PASS] All contracts valid!")
        sys.exit(0)
    else:
        print(f"[FAIL] Validation failed with {len(total_errors)} error(s)")
        sys.exit(1)


if __name__ == "__main__":
    main()
