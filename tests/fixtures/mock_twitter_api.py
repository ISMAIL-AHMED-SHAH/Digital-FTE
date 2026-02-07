"""
Mock Twitter API v2 responses for testing.

This module provides mock responses for Twitter API v2 endpoints
used by the Twitter MCP server.
"""

from typing import Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import json


# =============================================================================
# Tweet Responses
# =============================================================================

MOCK_TWEET_CREATE_SUCCESS = {
    "data": {
        "id": "1234567890123456789",
        "text": "Hello, World! This is a test tweet from AI Employee.",
        "edit_history_tweet_ids": ["1234567890123456789"]
    }
}

MOCK_TWEET_WITH_MEDIA_SUCCESS = {
    "data": {
        "id": "1234567890123456790",
        "text": "Check out this image! #AIEmployee",
        "attachments": {
            "media_keys": ["3_1234567890123456789"]
        },
        "edit_history_tweet_ids": ["1234567890123456790"]
    }
}

MOCK_TWEET_REPLY_SUCCESS = {
    "data": {
        "id": "1234567890123456791",
        "text": "@user This is a reply tweet.",
        "conversation_id": "1234567890123456780",
        "in_reply_to_user_id": "9876543210",
        "edit_history_tweet_ids": ["1234567890123456791"]
    }
}

MOCK_TWEET_THREAD_SUCCESS = [
    {
        "data": {
            "id": "1234567890123456792",
            "text": "1/ This is the start of a thread about AI Employee capabilities.",
            "edit_history_tweet_ids": ["1234567890123456792"]
        }
    },
    {
        "data": {
            "id": "1234567890123456793",
            "text": "2/ It can manage your social media posts automatically.",
            "conversation_id": "1234567890123456792",
            "edit_history_tweet_ids": ["1234567890123456793"]
        }
    },
    {
        "data": {
            "id": "1234567890123456794",
            "text": "3/ And much more! Stay tuned. #automation",
            "conversation_id": "1234567890123456792",
            "edit_history_tweet_ids": ["1234567890123456794"]
        }
    }
]

MOCK_TWEET_DELETE_SUCCESS = {
    "data": {
        "deleted": True
    }
}


# =============================================================================
# User Responses
# =============================================================================

MOCK_USER_ME = {
    "data": {
        "id": "1234567890",
        "name": "AI Employee Demo",
        "username": "ai_employee_demo",
        "created_at": "2024-01-01T00:00:00.000Z",
        "description": "Automated social media management powered by AI",
        "public_metrics": {
            "followers_count": 1500,
            "following_count": 200,
            "tweet_count": 500,
            "listed_count": 10
        }
    }
}


# =============================================================================
# Media Upload Responses (v1.1 API)
# =============================================================================

MOCK_MEDIA_UPLOAD_INIT = {
    "media_id": 1234567890123456789,
    "media_id_string": "1234567890123456789",
    "expires_after_secs": 86400
}

MOCK_MEDIA_UPLOAD_APPEND = {}  # Empty on success

MOCK_MEDIA_UPLOAD_FINALIZE = {
    "media_id": 1234567890123456789,
    "media_id_string": "1234567890123456789",
    "media_key": "3_1234567890123456789",
    "size": 1024000,
    "expires_after_secs": 86400,
    "image": {
        "image_type": "image/jpeg",
        "w": 1200,
        "h": 800
    }
}

MOCK_MEDIA_UPLOAD_STATUS = {
    "media_id": 1234567890123456789,
    "media_id_string": "1234567890123456789",
    "processing_info": {
        "state": "succeeded",
        "progress_percent": 100
    }
}


# =============================================================================
# Rate Limit Responses
# =============================================================================

MOCK_RATE_LIMIT_STATUS = {
    "data": {
        "tweets": {
            "limit": 100,
            "remaining": 95,
            "reset": int((datetime.now() + timedelta(minutes=15)).timestamp())
        },
        "app_tweets": {
            "limit": 10000,
            "remaining": 9950,
            "reset": int((datetime.now() + timedelta(hours=24)).timestamp())
        }
    }
}


# =============================================================================
# Error Responses
# =============================================================================

MOCK_DUPLICATE_TWEET_ERROR = {
    "errors": [
        {
            "message": "You have already said that.",
            "code": 187
        }
    ],
    "title": "Forbidden",
    "detail": "You are not allowed to create a Tweet with duplicate content.",
    "type": "about:blank",
    "status": 403
}

MOCK_RATE_LIMIT_ERROR = {
    "errors": [
        {
            "message": "Rate limit exceeded",
            "code": 88
        }
    ],
    "title": "Too Many Requests",
    "detail": "Too Many Requests",
    "type": "about:blank",
    "status": 429
}

MOCK_AUTH_ERROR = {
    "errors": [
        {
            "message": "Invalid or expired token.",
            "code": 89
        }
    ],
    "title": "Unauthorized",
    "detail": "Unauthorized",
    "type": "about:blank",
    "status": 401
}

MOCK_CHARACTER_LIMIT_ERROR = {
    "errors": [
        {
            "message": "Tweet exceeds the maximum allowed character count.",
            "code": 186
        }
    ],
    "title": "Forbidden",
    "detail": "Tweet body too long.",
    "type": "about:blank",
    "status": 403
}

MOCK_TWEET_NOT_FOUND = {
    "errors": [
        {
            "value": "1234567890123456789",
            "detail": "Could not find tweet with id: [1234567890123456789].",
            "title": "Not Found Error",
            "resource_type": "tweet",
            "parameter": "id",
            "type": "https://api.twitter.com/2/problems/resource-not-found"
        }
    ]
}


# =============================================================================
# Tweet Metrics Responses
# =============================================================================

MOCK_TWEET_METRICS = {
    "data": {
        "id": "1234567890123456789",
        "text": "Hello, World! This is a test tweet from AI Employee.",
        "public_metrics": {
            "retweet_count": 25,
            "reply_count": 10,
            "like_count": 150,
            "quote_count": 5,
            "bookmark_count": 8,
            "impression_count": 5000
        },
        "created_at": "2026-02-05T12:00:00.000Z"
    }
}


# =============================================================================
# Mock API Client
# =============================================================================

class MockTwitterClient:
    """Mock Twitter API v2 client for testing."""

    def __init__(
        self,
        should_fail: bool = False,
        rate_limited: bool = False,
        auth_error: bool = False
    ):
        """
        Initialize mock client.

        Args:
            should_fail: If True, all calls will fail
            rate_limited: If True, return rate limit errors
            auth_error: If True, return auth errors
        """
        self.should_fail = should_fail
        self.rate_limited = rate_limited
        self.auth_error = auth_error
        self.calls: list[dict] = []
        self._tweet_counter = 1234567890123456789

    def tweet(self, text: str, **kwargs) -> dict:
        """Mock tweet creation."""
        self.calls.append({
            "method": "tweet",
            "text": text,
            "kwargs": kwargs
        })

        if self.should_fail:
            raise ConnectionError("Connection failed")

        if self.rate_limited:
            return MOCK_RATE_LIMIT_ERROR

        if self.auth_error:
            return MOCK_AUTH_ERROR

        # Check character limit
        if len(text) > 280:
            return MOCK_CHARACTER_LIMIT_ERROR

        self._tweet_counter += 1
        return {
            "data": {
                "id": str(self._tweet_counter),
                "text": text,
                "edit_history_tweet_ids": [str(self._tweet_counter)]
            }
        }

    def delete_tweet(self, tweet_id: str) -> dict:
        """Mock tweet deletion."""
        self.calls.append({
            "method": "delete_tweet",
            "tweet_id": tweet_id
        })

        if self.should_fail:
            raise ConnectionError("Connection failed")

        return MOCK_TWEET_DELETE_SUCCESS

    def get_me(self) -> dict:
        """Mock get authenticated user."""
        self.calls.append({"method": "get_me"})

        if self.auth_error:
            return MOCK_AUTH_ERROR

        return MOCK_USER_ME

    def get_tweet(self, tweet_id: str, **kwargs) -> dict:
        """Mock get tweet."""
        self.calls.append({
            "method": "get_tweet",
            "tweet_id": tweet_id,
            "kwargs": kwargs
        })

        if self.should_fail:
            return MOCK_TWEET_NOT_FOUND

        return MOCK_TWEET_METRICS

    def upload_media(self, media_path: str, **kwargs) -> str:
        """Mock media upload (v1.1 API)."""
        self.calls.append({
            "method": "upload_media",
            "media_path": media_path,
            "kwargs": kwargs
        })

        if self.should_fail:
            raise ConnectionError("Media upload failed")

        return "1234567890123456789"

    def reset(self):
        """Reset call tracking."""
        self.calls = []
        self._tweet_counter = 1234567890123456789


# =============================================================================
# Tweet Validation
# =============================================================================

def validate_tweet_text(text: str) -> dict:
    """
    Validate tweet text and return validation result.

    Args:
        text: Tweet text to validate

    Returns:
        Validation result dict
    """
    # Twitter counts URLs as 23 characters
    url_pattern = r'https?://\S+'
    import re

    urls = re.findall(url_pattern, text)
    url_adjusted_length = len(text)

    for url in urls:
        # Replace URL with 23-character placeholder for counting
        url_adjusted_length = url_adjusted_length - len(url) + 23

    # Extract mentions and hashtags
    mentions = re.findall(r'@(\w+)', text)
    hashtags = re.findall(r'#(\w+)', text)

    return {
        "valid": url_adjusted_length <= 280,
        "character_count": url_adjusted_length,
        "characters_remaining": 280 - url_adjusted_length,
        "urls_detected": urls,
        "mentions_detected": mentions,
        "hashtags_detected": hashtags,
        "validation_errors": [] if url_adjusted_length <= 280 else [
            f"Tweet exceeds 280 character limit ({url_adjusted_length} characters)"
        ]
    }


# =============================================================================
# Test Data Generators
# =============================================================================

def generate_tweet_data(
    text: str = "Test tweet from AI Employee",
    reply_to: str | None = None,
    quote_tweet_id: str | None = None,
    media_ids: list[str] | None = None
) -> dict:
    """Generate test tweet data."""
    data = {"text": text}

    if reply_to:
        data["reply"] = {"in_reply_to_tweet_id": reply_to}
    if quote_tweet_id:
        data["quote_tweet_id"] = quote_tweet_id
    if media_ids:
        data["media"] = {"media_ids": media_ids}

    return data


def generate_thread_data(tweets: list[str]) -> list[dict]:
    """Generate test thread data."""
    return [{"text": tweet} for tweet in tweets]


# =============================================================================
# Fixtures for pytest
# =============================================================================

def pytest_fixtures():
    """Return fixtures for pytest."""
    return {
        "mock_twitter_client": MockTwitterClient(),
        "mock_failing_client": MockTwitterClient(should_fail=True),
        "mock_rate_limited_client": MockTwitterClient(rate_limited=True),
        "mock_auth_error_client": MockTwitterClient(auth_error=True),
        "mock_user": MOCK_USER_ME,
        "mock_tweet": MOCK_TWEET_CREATE_SUCCESS
    }
