"""
Mock Meta Graph API responses for testing.

This module provides mock responses for Meta Business Suite API endpoints
used by the Facebook and Instagram MCP servers.
"""

from typing import Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import json


# =============================================================================
# OAuth Token Responses
# =============================================================================

def get_mock_access_token(expires_in: int = 5184000) -> dict:
    """Generate mock access token response (60 days default)."""
    return {
        "access_token": "mock_access_token_" + datetime.now().strftime("%Y%m%d%H%M%S"),
        "token_type": "bearer",
        "expires_in": expires_in
    }


MOCK_TOKEN_EXCHANGE_SUCCESS = {
    "access_token": "mock_long_lived_token_abc123",
    "token_type": "bearer",
    "expires_in": 5184000  # 60 days
}

MOCK_TOKEN_EXPIRED = {
    "error": {
        "message": "Error validating access token: Session has expired",
        "type": "OAuthException",
        "code": 190,
        "error_subcode": 463,
        "fbtrace_id": "mock_trace_id"
    }
}

MOCK_TOKEN_DEBUG = {
    "data": {
        "app_id": "123456789",
        "type": "PAGE",
        "application": "AI Employee App",
        "data_access_expires_at": int((datetime.now() + timedelta(days=90)).timestamp()),
        "expires_at": int((datetime.now() + timedelta(days=60)).timestamp()),
        "is_valid": True,
        "scopes": [
            "pages_manage_posts",
            "pages_read_engagement",
            "instagram_basic",
            "instagram_content_publishing"
        ],
        "user_id": "100000000000001"
    }
}


# =============================================================================
# Facebook Page Responses
# =============================================================================

MOCK_PAGE_INFO = {
    "id": "123456789012345",
    "name": "AI Employee Demo Page",
    "category": "Software Company",
    "followers_count": 1500,
    "fan_count": 1450,
    "access_token": "mock_page_access_token"
}

MOCK_PAGE_ACCOUNTS = {
    "data": [
        {
            "id": "123456789012345",
            "name": "AI Employee Demo Page",
            "access_token": "mock_page_token_1",
            "category": "Software Company",
            "instagram_business_account": {
                "id": "17841400000000001"
            }
        }
    ],
    "paging": {
        "cursors": {
            "before": "mock_cursor_before",
            "after": "mock_cursor_after"
        }
    }
}


# =============================================================================
# Facebook Post Responses
# =============================================================================

MOCK_POST_CREATE_SUCCESS = {
    "id": "123456789012345_987654321098765"
}

MOCK_POST_SCHEDULED_SUCCESS = {
    "id": "123456789012345_987654321098766",
    "scheduled_publish_time": int((datetime.now() + timedelta(hours=24)).timestamp())
}

MOCK_POST_CREATE_ERROR = {
    "error": {
        "message": "(#200) Requires extended permission: publish_actions",
        "type": "OAuthException",
        "code": 200,
        "fbtrace_id": "mock_trace_id"
    }
}

MOCK_POST_RATE_LIMITED = {
    "error": {
        "message": "(#32) Page request limit reached",
        "type": "OAuthException",
        "code": 32,
        "fbtrace_id": "mock_trace_id"
    }
}

MOCK_POST_INSIGHTS = {
    "data": [
        {
            "name": "post_impressions",
            "period": "lifetime",
            "values": [{"value": 1500}],
            "title": "Lifetime Post Total Impressions"
        },
        {
            "name": "post_engaged_users",
            "period": "lifetime",
            "values": [{"value": 250}],
            "title": "Lifetime Engaged Users"
        },
        {
            "name": "post_clicks",
            "period": "lifetime",
            "values": [{"value": 75}],
            "title": "Lifetime Post Clicks"
        }
    ]
}


# =============================================================================
# Instagram Responses
# =============================================================================

MOCK_IG_ACCOUNT_INFO = {
    "id": "17841400000000001",
    "username": "ai_employee_demo",
    "name": "AI Employee Demo",
    "followers_count": 2500,
    "follows_count": 150,
    "media_count": 45,
    "profile_picture_url": "https://example.com/profile.jpg"
}

# Container creation (step 1 of Instagram publishing)
MOCK_IG_CONTAINER_CREATE_SUCCESS = {
    "id": "17889455560051444"
}

MOCK_IG_CONTAINER_STATUS_IN_PROGRESS = {
    "id": "17889455560051444",
    "status": "IN_PROGRESS"
}

MOCK_IG_CONTAINER_STATUS_FINISHED = {
    "id": "17889455560051444",
    "status": "FINISHED",
    "status_code": "PUBLISHED"
}

MOCK_IG_CONTAINER_STATUS_ERROR = {
    "id": "17889455560051444",
    "status": "ERROR",
    "status_code": "INVALID_ASPEC_RATIO"
}

# Media publish (step 2 of Instagram publishing)
MOCK_IG_PUBLISH_SUCCESS = {
    "id": "17889455560051445"
}

MOCK_IG_MEDIA_INFO = {
    "id": "17889455560051445",
    "caption": "Test post from AI Employee #automation",
    "media_type": "IMAGE",
    "media_url": "https://example.com/media.jpg",
    "permalink": "https://www.instagram.com/p/ABC123/",
    "timestamp": "2026-02-05T12:00:00+0000"
}

MOCK_IG_MEDIA_INSIGHTS = {
    "data": [
        {
            "name": "impressions",
            "period": "lifetime",
            "values": [{"value": 3500}]
        },
        {
            "name": "reach",
            "period": "lifetime",
            "values": [{"value": 2800}]
        },
        {
            "name": "engagement",
            "period": "lifetime",
            "values": [{"value": 450}]
        },
        {
            "name": "saved",
            "period": "lifetime",
            "values": [{"value": 25}]
        }
    ]
}

MOCK_IG_RATE_LIMITED = {
    "error": {
        "message": "Application request limit reached",
        "type": "OAuthException",
        "code": 4,
        "error_subcode": 2207051,
        "fbtrace_id": "mock_trace_id"
    }
}

MOCK_IG_ASPECT_RATIO_ERROR = {
    "error": {
        "message": "The submitted image has an aspect ratio that is not allowed",
        "type": "GraphMethodException",
        "code": 36003,
        "error_subcode": 2207027,
        "fbtrace_id": "mock_trace_id"
    }
}


# =============================================================================
# Error Responses
# =============================================================================

MOCK_PERMISSION_ERROR = {
    "error": {
        "message": "(#200) Permissions error",
        "type": "OAuthException",
        "code": 200,
        "fbtrace_id": "mock_trace_id"
    }
}

MOCK_INVALID_PARAMETER = {
    "error": {
        "message": "Invalid parameter",
        "type": "GraphMethodException",
        "code": 100,
        "fbtrace_id": "mock_trace_id"
    }
}

MOCK_NETWORK_ERROR = {
    "error": "Connection timeout"
}


# =============================================================================
# Mock API Client
# =============================================================================

class MockMetaGraphClient:
    """Mock Meta Graph API client for testing."""

    def __init__(
        self,
        should_fail: bool = False,
        token_expired: bool = False,
        rate_limited: bool = False
    ):
        """
        Initialize mock client.

        Args:
            should_fail: If True, all calls will fail
            token_expired: If True, return token expired errors
            rate_limited: If True, return rate limit errors
        """
        self.should_fail = should_fail
        self.token_expired = token_expired
        self.rate_limited = rate_limited
        self.calls: list[dict] = []
        self._container_status = "IN_PROGRESS"
        self._container_polls = 0

    def get(self, endpoint: str, params: dict | None = None) -> dict:
        """Mock GET request."""
        self.calls.append({
            "method": "GET",
            "endpoint": endpoint,
            "params": params
        })

        if self.should_fail:
            return MOCK_NETWORK_ERROR

        if self.token_expired:
            return MOCK_TOKEN_EXPIRED

        if self.rate_limited:
            return MOCK_POST_RATE_LIMITED

        # Route to appropriate mock response
        if "/me/accounts" in endpoint:
            return MOCK_PAGE_ACCOUNTS
        elif "/debug_token" in endpoint:
            return MOCK_TOKEN_DEBUG
        elif "/insights" in endpoint:
            if "instagram" in endpoint.lower() or "media" in endpoint:
                return MOCK_IG_MEDIA_INSIGHTS
            return MOCK_POST_INSIGHTS
        elif endpoint.endswith("/media"):
            return {"data": [MOCK_IG_MEDIA_INFO]}
        elif "?fields=status" in endpoint or "status" in str(params):
            # Container status polling
            self._container_polls += 1
            if self._container_polls >= 2:
                return MOCK_IG_CONTAINER_STATUS_FINISHED
            return MOCK_IG_CONTAINER_STATUS_IN_PROGRESS

        return {"data": []}

    def post(self, endpoint: str, data: dict | None = None) -> dict:
        """Mock POST request."""
        self.calls.append({
            "method": "POST",
            "endpoint": endpoint,
            "data": data
        })

        if self.should_fail:
            return MOCK_NETWORK_ERROR

        if self.token_expired:
            return MOCK_TOKEN_EXPIRED

        if self.rate_limited:
            return MOCK_POST_RATE_LIMITED

        # Route to appropriate mock response
        if "/feed" in endpoint:
            if data and "scheduled_publish_time" in data:
                return MOCK_POST_SCHEDULED_SUCCESS
            return MOCK_POST_CREATE_SUCCESS
        elif "/media" in endpoint and "creation_id" not in str(data):
            # Container creation
            return MOCK_IG_CONTAINER_CREATE_SUCCESS
        elif "/media_publish" in endpoint or "creation_id" in str(data):
            # Media publish
            return MOCK_IG_PUBLISH_SUCCESS
        elif "/oauth/access_token" in endpoint:
            return MOCK_TOKEN_EXCHANGE_SUCCESS

        return {"id": "mock_response_id"}

    def delete(self, endpoint: str) -> dict:
        """Mock DELETE request."""
        self.calls.append({
            "method": "DELETE",
            "endpoint": endpoint
        })

        if self.should_fail:
            return MOCK_NETWORK_ERROR

        return {"success": True}

    def reset(self):
        """Reset call tracking."""
        self.calls = []
        self._container_polls = 0


# =============================================================================
# Test Data Generators
# =============================================================================

def generate_facebook_post_data(
    page_id: str = "123456789012345",
    message: str = "Test post from AI Employee",
    link: str | None = None,
    image_url: str | None = None,
    scheduled_time: datetime | None = None
) -> dict:
    """Generate test Facebook post data."""
    data = {
        "page_id": page_id,
        "message": message
    }

    if link:
        data["link"] = link
    if image_url:
        data["image_url"] = image_url
    if scheduled_time:
        data["scheduled_publish_time"] = int(scheduled_time.timestamp())

    return data


def generate_instagram_post_data(
    ig_user_id: str = "17841400000000001",
    media_type: str = "IMAGE",
    media_urls: list[str] | None = None,
    caption: str = "Test post from AI Employee #automation"
) -> dict:
    """Generate test Instagram post data."""
    if media_urls is None:
        media_urls = ["https://example.com/test-image.jpg"]

    return {
        "ig_user_id": ig_user_id,
        "media_type": media_type,
        "media_urls": media_urls,
        "caption": caption
    }


# =============================================================================
# Fixtures for pytest
# =============================================================================

def pytest_fixtures():
    """Return fixtures for pytest."""
    return {
        "mock_meta_client": MockMetaGraphClient(),
        "mock_failing_client": MockMetaGraphClient(should_fail=True),
        "mock_expired_token_client": MockMetaGraphClient(token_expired=True),
        "mock_rate_limited_client": MockMetaGraphClient(rate_limited=True),
        "mock_page_info": MOCK_PAGE_INFO,
        "mock_ig_account_info": MOCK_IG_ACCOUNT_INFO
    }
