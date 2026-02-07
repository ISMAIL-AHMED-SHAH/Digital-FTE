#!/usr/bin/env python3
"""Social Operations Skill - Main Operation (T050).

Multi-platform social media management for AI Employee.

Supports:
- LinkedIn: Text posts (Silver Tier)
- Facebook: Page posts with text, links, photos (Gold Tier)
- Instagram: Photo, video, reels, carousel posts (Gold Tier)
- Twitter: Tweets with character validation (Gold Tier)

Usage:
    python main_operation.py --action post --platform facebook --content "Hello world!"
    python main_operation.py --action post --platform instagram --image-url URL --caption "Caption"
    python main_operation.py --action schedule --platform facebook --content "Post" --time "2026-02-10T09:00:00"
    python main_operation.py --action status
"""

import argparse
import sys
import json
import os
import difflib
from pathlib import Path
from datetime import datetime
from typing import Any

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
VAULT_ROOT = Path(os.environ.get("VAULT_PATH", PROJECT_ROOT / "vault"))
LOGS_DIR = VAULT_ROOT / "Logs"
DATA_DIR = PROJECT_ROOT / "data"
APPROVALS_DIR = DATA_DIR / "approvals"
IDEMPOTENCY_DB = DATA_DIR / "idempotency.db"

# MCP server directories
MCP_SERVERS = {
    "linkedin": PROJECT_ROOT / "src" / "mcp_servers" / "linkedin",
    "facebook": PROJECT_ROOT / "src" / "mcp_servers" / "facebook",
    "instagram": PROJECT_ROOT / "src" / "mcp_servers" / "instagram",
    "twitter": PROJECT_ROOT / "src" / "mcp_servers" / "twitter",
}

# Platform limits
PLATFORM_LIMITS = {
    "linkedin": {"chars": 3000, "hashtags": None},
    "facebook": {"chars": 63206, "hashtags": None},
    "instagram": {"chars": 2200, "hashtags": 30},
    "twitter": {"chars": 280, "hashtags": None},
}

# Fallback log files
DRY_RUN_LOG = LOGS_DIR / "Social_Dry_Run.log"
AUDIT_LOG = LOGS_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.json"


def setup_dirs():
    """Ensure required directories exist."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    APPROVALS_DIR.mkdir(parents=True, exist_ok=True)


def output_json(data: dict) -> None:
    """Output data as JSON to stdout."""
    print(json.dumps(data, indent=2, default=str))


def output_error(message: str, code: str = "SKILL_ERROR") -> None:
    """Output error as JSON."""
    output_json({
        "success": False,
        "error": {"code": code, "message": message}
    })
    sys.exit(1)


def audit_log(action: str, platform: str, result: str, details: dict = None):
    """Write audit log entry."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "component": "social_ops_skill",
        "action_type": action,
        "target": platform,
        "result": result,
        "parameters": details or {}
    }

    try:
        if AUDIT_LOG.exists():
            with open(AUDIT_LOG, 'r') as f:
                logs = json.load(f)
        else:
            logs = []
        logs.append(entry)
        with open(AUDIT_LOG, 'w') as f:
            json.dump(logs, f, indent=2)
    except Exception as e:
        print(f"Warning: Audit log failed: {e}", file=sys.stderr)


def check_mcp_server_available(platform: str) -> bool:
    """Check if MCP server is available for platform."""
    if platform not in MCP_SERVERS:
        return False
    server_dir = MCP_SERVERS[platform]
    return (server_dir / "dist" / "index.js").exists() or \
           (server_dir / "src" / "index.ts").exists()


def validate_content(content: str, platform: str) -> dict:
    """Validate content against platform limits."""
    limits = PLATFORM_LIMITS.get(platform, {})

    # Check character limit
    char_limit = limits.get("chars")
    if char_limit and len(content) > char_limit:
        return {
            "valid": False,
            "error": f"Content exceeds {char_limit} character limit ({len(content)} chars)"
        }

    # Check hashtag limit (Instagram)
    hashtag_limit = limits.get("hashtags")
    if hashtag_limit:
        hashtag_count = content.count("#")
        if hashtag_count > hashtag_limit:
            return {
                "valid": False,
                "error": f"Too many hashtags ({hashtag_count}). Maximum is {hashtag_limit}."
            }

    return {"valid": True}


def check_duplicates(content: str, platform: str) -> bool:
    """Check for duplicate content in recent posts."""
    if not DRY_RUN_LOG.exists():
        return False

    with open(DRY_RUN_LOG, 'r') as f:
        posts = []
        for line in f:
            if f'[{platform}]' in line.lower() and '| Content: ' in line:
                post_content = line.split('| Content: ')[1].strip()
                posts.append(post_content)

    for post in posts[-10:]:
        ratio = difflib.SequenceMatcher(None, content, post).ratio()
        if ratio > 0.8:
            return True
    return False


def create_approval_file(platform: str, post_data: dict) -> str:
    """Create HITL approval file for Gold Tier platforms."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{platform}-post-{timestamp}.json"
    filepath = APPROVALS_DIR / filename

    approval_data = {
        "type": "social_post",
        "platform": platform,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "post_data": post_data,
    }

    with open(filepath, 'w') as f:
        json.dump(approval_data, f, indent=2)

    # Also create markdown file in vault
    vault_approval = VAULT_ROOT / "Needs_Action" / f"{platform}-post-{timestamp}.md"
    vault_approval.parent.mkdir(parents=True, exist_ok=True)

    content = post_data.get("content") or post_data.get("caption") or post_data.get("message", "")
    md_content = f"""---
type: social_post
platform: {platform}
status: pending
created: {datetime.now().isoformat()}
approval_file: {filepath}
---

# {platform.title()} Post Approval Required

## Content

{content}

## Actions

- [ ] **Approve**: Move this file to `/Done` folder to publish
- [ ] **Reject**: Move to `/Rejected` folder with reason

## Post Data

```json
{json.dumps(post_data, indent=2)}
```
"""
    vault_approval.write_text(md_content)

    return str(filepath)


# =============================================================================
# LinkedIn Operations (Silver Tier)
# =============================================================================

def post_linkedin(content: str, visibility: str = "PUBLIC", dry_run: bool = False) -> dict:
    """Create LinkedIn post."""
    validation = validate_content(content, "linkedin")
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    if check_duplicates(content, "linkedin"):
        return {"success": False, "error": "Duplicate content detected (>80% similar to recent post)"}

    if dry_run:
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [LINKEDIN] [DRY RUN] Visibility: {visibility} | Content: {content[:100]}...\n"
        with open(DRY_RUN_LOG, 'a') as f:
            f.write(log_entry)

        audit_log("create_post", "linkedin", "success (dry_run)", {"content_preview": content[:100]})
        return {
            "success": True,
            "platform": "linkedin",
            "post_id": "dry-run-linkedin-post",
            "dry_run": True
        }

    # Real LinkedIn posting requires MCP server integration via Claude
    return {
        "success": False,
        "error": "Direct LinkedIn posting requires MCP server. Use through Claude."
    }


# =============================================================================
# Facebook Operations (Gold Tier)
# =============================================================================

def post_facebook(
    content: str,
    page_id: str = None,
    link: str = None,
    photo_url: str = None,
    scheduled_time: str = None,
    require_approval: bool = True,
    dry_run: bool = False
) -> dict:
    """Create Facebook Page post."""
    page_id = page_id or os.environ.get("META_PAGE_ID")
    if not page_id:
        return {"success": False, "error": "page_id required (or set META_PAGE_ID)"}

    validation = validate_content(content, "facebook")
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    post_data = {
        "page_id": page_id,
        "message": content,
        "link": link,
        "photo_url": photo_url,
        "scheduled_publish_time": scheduled_time,
    }

    # HITL approval for production posts
    if require_approval and not dry_run:
        approval_file = create_approval_file("facebook", post_data)
        audit_log("create_post", "facebook", "pending_approval", {"approval_file": approval_file})
        return {
            "success": True,
            "platform": "facebook",
            "status": "pending_approval",
            "approval_file": approval_file,
        }

    if dry_run:
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [FACEBOOK] [DRY RUN] Page: {page_id} | Content: {content[:100]}...\n"
        with open(DRY_RUN_LOG, 'a') as f:
            f.write(log_entry)

        audit_log("create_post", "facebook", "success (dry_run)", {"content_preview": content[:100]})
        return {
            "success": True,
            "platform": "facebook",
            "post_id": "dry-run-facebook-post",
            "dry_run": True,
        }

    return {
        "success": False,
        "error": "Direct Facebook posting requires MCP server. Use through Claude."
    }


# =============================================================================
# Instagram Operations (Gold Tier)
# =============================================================================

def post_instagram(
    account_id: str = None,
    image_url: str = None,
    video_url: str = None,
    caption: str = None,
    media_type: str = None,
    require_approval: bool = True,
    dry_run: bool = False
) -> dict:
    """Create Instagram post."""
    account_id = account_id or os.environ.get("META_INSTAGRAM_ID")
    if not account_id:
        return {"success": False, "error": "account_id required (or set META_INSTAGRAM_ID)"}

    if not image_url and not video_url:
        return {"success": False, "error": "image_url or video_url required"}

    if caption:
        validation = validate_content(caption, "instagram")
        if not validation["valid"]:
            return {"success": False, "error": validation["error"]}

    post_data = {
        "account_id": account_id,
        "image_url": image_url,
        "video_url": video_url,
        "caption": caption,
        "media_type": media_type or ("VIDEO" if video_url else "IMAGE"),
    }

    # HITL approval for production posts
    if require_approval and not dry_run:
        approval_file = create_approval_file("instagram", post_data)
        audit_log("create_post", "instagram", "pending_approval", {"approval_file": approval_file})
        return {
            "success": True,
            "platform": "instagram",
            "status": "pending_approval",
            "approval_file": approval_file,
        }

    if dry_run:
        timestamp = datetime.now().isoformat()
        media = image_url or video_url
        log_entry = f"[{timestamp}] [INSTAGRAM] [DRY RUN] Account: {account_id} | Media: {media[:50]}... | Caption: {(caption or '')[:50]}...\n"
        with open(DRY_RUN_LOG, 'a') as f:
            f.write(log_entry)

        audit_log("create_post", "instagram", "success (dry_run)", {"caption_preview": (caption or "")[:100]})
        return {
            "success": True,
            "platform": "instagram",
            "media_id": "dry-run-instagram-media",
            "dry_run": True,
        }

    return {
        "success": False,
        "error": "Direct Instagram posting requires MCP server. Use through Claude."
    }


# =============================================================================
# Twitter Operations (Gold Tier - Placeholder)
# =============================================================================

def post_twitter(
    content: str,
    require_approval: bool = True,
    dry_run: bool = False
) -> dict:
    """Create Twitter post (placeholder - full implementation in Phase 6)."""
    validation = validate_content(content, "twitter")
    if not validation["valid"]:
        return {"success": False, "error": validation["error"]}

    post_data = {"text": content}

    if require_approval and not dry_run:
        approval_file = create_approval_file("twitter", post_data)
        audit_log("create_post", "twitter", "pending_approval", {"approval_file": approval_file})
        return {
            "success": True,
            "platform": "twitter",
            "status": "pending_approval",
            "approval_file": approval_file,
        }

    if dry_run:
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [TWITTER] [DRY RUN] Content: {content}\n"
        with open(DRY_RUN_LOG, 'a') as f:
            f.write(log_entry)

        audit_log("create_post", "twitter", "success (dry_run)", {"content": content})
        return {
            "success": True,
            "platform": "twitter",
            "tweet_id": "dry-run-twitter-tweet",
            "dry_run": True,
        }

    return {
        "success": False,
        "error": "Twitter MCP server not yet implemented. Coming in Phase 6."
    }


# =============================================================================
# Cross-Platform Operations
# =============================================================================

def cross_post(
    content: str,
    platforms: list[str],
    require_approval: bool = True,
    dry_run: bool = False,
    **kwargs
) -> dict:
    """Post to multiple platforms."""
    results = {}

    for platform in platforms:
        if platform == "linkedin":
            results["linkedin"] = post_linkedin(content, dry_run=dry_run)
        elif platform == "facebook":
            results["facebook"] = post_facebook(
                content,
                page_id=kwargs.get("page_id"),
                require_approval=require_approval,
                dry_run=dry_run
            )
        elif platform == "instagram":
            # Instagram requires image, so skip if not provided
            if not kwargs.get("image_url"):
                results["instagram"] = {"success": False, "error": "Instagram requires image_url"}
            else:
                results["instagram"] = post_instagram(
                    account_id=kwargs.get("account_id"),
                    image_url=kwargs.get("image_url"),
                    caption=content,
                    require_approval=require_approval,
                    dry_run=dry_run
                )
        elif platform == "twitter":
            # Truncate for Twitter
            tweet_content = content[:280] if len(content) > 280 else content
            results["twitter"] = post_twitter(
                tweet_content,
                require_approval=require_approval,
                dry_run=dry_run
            )

    return {
        "success": all(r.get("success") for r in results.values()),
        "results": results,
    }


# =============================================================================
# Status and List Operations
# =============================================================================

def list_recent(platform: str = "all", limit: int = 5):
    """List recent posts from logs."""
    posts = []

    # Check dry-run log
    if DRY_RUN_LOG.exists():
        with open(DRY_RUN_LOG, 'r') as f:
            for line in f:
                if platform == "all" or f"[{platform.upper()}]" in line:
                    posts.append(line.strip())

    # Check approval files
    if APPROVALS_DIR.exists():
        for file in sorted(APPROVALS_DIR.glob("*.json"), reverse=True)[:limit]:
            try:
                with open(file) as f:
                    data = json.load(f)
                    if platform == "all" or data.get("platform") == platform:
                        posts.append(f"[{data.get('created_at')}] [{data.get('platform', 'unknown').upper()}] Status: {data.get('status')} | File: {file.name}")
            except Exception:
                pass

    output_json({
        "success": True,
        "posts": posts[-limit:] if posts else [],
        "count": len(posts[-limit:]),
    })


def check_status():
    """Check status of all social media platforms."""
    status = {
        "platforms": {},
        "mcp_servers": {},
        "credentials": {},
    }

    # Check MCP servers
    for platform, server_dir in MCP_SERVERS.items():
        status["mcp_servers"][platform] = check_mcp_server_available(platform)

    # Check credentials
    status["credentials"]["linkedin"] = bool(os.environ.get("LINKEDIN_ACCESS_TOKEN"))
    status["credentials"]["facebook"] = bool(os.environ.get("META_ACCESS_TOKEN"))
    status["credentials"]["instagram"] = bool(os.environ.get("META_ACCESS_TOKEN"))
    status["credentials"]["twitter"] = bool(os.environ.get("TWITTER_API_KEY"))

    # Check dry-run mode
    status["dry_run_mode"] = os.environ.get("DRY_RUN", "").lower() == "true"

    # Check pending approvals
    pending = 0
    if APPROVALS_DIR.exists():
        for file in APPROVALS_DIR.glob("*.json"):
            try:
                with open(file) as f:
                    data = json.load(f)
                    if data.get("status") == "pending":
                        pending += 1
            except Exception:
                pass
    status["pending_approvals"] = pending

    output_json({"success": True, "status": status})


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Social Operations Skill - Multi-platform social media management"
    )
    parser.add_argument(
        "--action", required=True,
        choices=["post", "schedule", "list-recent", "status", "cross-post"],
        help="Action to perform"
    )
    parser.add_argument(
        "--platform",
        choices=["linkedin", "facebook", "instagram", "twitter", "all"],
        help="Target platform"
    )
    parser.add_argument("--platforms", help="Comma-separated platforms for cross-post")
    parser.add_argument("--content", help="Post content/message")
    parser.add_argument("--caption", help="Caption (Instagram)")
    parser.add_argument("--page-id", help="Facebook Page ID")
    parser.add_argument("--account-id", help="Instagram Account ID")
    parser.add_argument("--image-url", help="Image URL (Instagram/Facebook)")
    parser.add_argument("--video-url", help="Video URL (Instagram)")
    parser.add_argument("--link", help="Link URL (Facebook)")
    parser.add_argument("--time", help="Scheduled time (ISO8601)")
    parser.add_argument("--visibility", default="PUBLIC", help="LinkedIn visibility")
    parser.add_argument("--limit", type=int, default=5, help="Limit for list-recent")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without posting")
    parser.add_argument("--no-approval", action="store_true", help="Skip HITL approval")

    args = parser.parse_args()
    setup_dirs()

    dry_run = args.dry_run or os.environ.get("DRY_RUN", "").lower() == "true"
    require_approval = not args.no_approval

    try:
        if args.action == "post":
            if not args.platform:
                output_error("--platform required for post action")

            if args.platform == "linkedin":
                if not args.content:
                    output_error("--content required for LinkedIn post")
                result = post_linkedin(args.content, args.visibility, dry_run)

            elif args.platform == "facebook":
                if not args.content:
                    output_error("--content required for Facebook post")
                result = post_facebook(
                    args.content,
                    page_id=args.page_id,
                    link=args.link,
                    photo_url=args.image_url,
                    scheduled_time=args.time,
                    require_approval=require_approval,
                    dry_run=dry_run
                )

            elif args.platform == "instagram":
                result = post_instagram(
                    account_id=args.account_id,
                    image_url=args.image_url,
                    video_url=args.video_url,
                    caption=args.caption or args.content,
                    require_approval=require_approval,
                    dry_run=dry_run
                )

            elif args.platform == "twitter":
                if not args.content:
                    output_error("--content required for Twitter post")
                result = post_twitter(args.content, require_approval, dry_run)

            output_json(result)

        elif args.action == "schedule":
            if not args.platform or not args.time:
                output_error("--platform and --time required for schedule action")
            if args.platform != "facebook":
                output_error("Scheduling currently only supported for Facebook")

            result = post_facebook(
                args.content,
                page_id=args.page_id,
                scheduled_time=args.time,
                require_approval=require_approval,
                dry_run=dry_run
            )
            output_json(result)

        elif args.action == "cross-post":
            if not args.platforms:
                output_error("--platforms required (comma-separated)")
            if not args.content:
                output_error("--content required for cross-post")

            platforms = [p.strip() for p in args.platforms.split(",")]
            result = cross_post(
                args.content,
                platforms,
                require_approval=require_approval,
                dry_run=dry_run,
                page_id=args.page_id,
                account_id=args.account_id,
                image_url=args.image_url
            )
            output_json(result)

        elif args.action == "list-recent":
            list_recent(args.platform or "all", args.limit)

        elif args.action == "status":
            check_status()

    except Exception as e:
        output_error(str(e), "EXECUTION_ERROR")


if __name__ == "__main__":
    main()
