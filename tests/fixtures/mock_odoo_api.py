"""
Mock Odoo JSON-RPC API responses for testing.

This module provides mock responses for Odoo JSON-RPC API endpoints
used by the Odoo MCP server.
"""

from typing import Any
from dataclasses import dataclass, field
from datetime import datetime, date
import json


@dataclass
class MockOdooResponse:
    """Base class for mock Odoo JSON-RPC responses."""

    jsonrpc: str = "2.0"
    id: int = 1
    result: Any = None
    error: dict | None = None


# =============================================================================
# Authentication Responses
# =============================================================================

MOCK_AUTH_SUCCESS = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": 2  # User ID
}

MOCK_AUTH_FAILURE = {
    "jsonrpc": "2.0",
    "id": 1,
    "error": {
        "code": -32097,
        "message": "Access Denied",
        "data": {
            "name": "odoo.exceptions.AccessDenied",
            "debug": "Invalid username or password"
        }
    }
}

MOCK_VERSION_INFO = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "server_version": "19.0",
        "server_version_info": [19, 0, 0, "final", 0],
        "server_serie": "19.0",
        "protocol_version": 1
    }
}


# =============================================================================
# Partner (Customer) Responses
# =============================================================================

MOCK_PARTNERS = [
    {
        "id": 1,
        "name": "Acme Corporation",
        "email": "contact@acme.com",
        "phone": "+1-555-0100",
        "is_company": True,
        "customer_rank": 5,
        "credit_limit": 50000.00
    },
    {
        "id": 2,
        "name": "TechStart Inc",
        "email": "info@techstart.io",
        "phone": "+1-555-0200",
        "is_company": True,
        "customer_rank": 3,
        "credit_limit": 25000.00
    },
    {
        "id": 3,
        "name": "Global Services Ltd",
        "email": "support@globalservices.com",
        "phone": "+1-555-0300",
        "is_company": True,
        "customer_rank": 4,
        "credit_limit": 35000.00
    }
]

MOCK_PARTNER_SEARCH = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": [p["id"] for p in MOCK_PARTNERS]
}

MOCK_PARTNER_READ = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": MOCK_PARTNERS
}


# =============================================================================
# Invoice Responses
# =============================================================================

MOCK_INVOICES = [
    {
        "id": 101,
        "name": "INV/2026/00001",
        "move_type": "out_invoice",
        "partner_id": [1, "Acme Corporation"],
        "invoice_date": "2026-02-01",
        "invoice_date_due": "2026-03-01",
        "amount_untaxed": 5000.00,
        "amount_tax": 400.00,
        "amount_total": 5400.00,
        "amount_residual": 5400.00,
        "state": "posted",
        "payment_state": "not_paid"
    },
    {
        "id": 102,
        "name": "INV/2026/00002",
        "move_type": "out_invoice",
        "partner_id": [2, "TechStart Inc"],
        "invoice_date": "2026-02-03",
        "invoice_date_due": "2026-03-03",
        "amount_untaxed": 2500.00,
        "amount_tax": 200.00,
        "amount_total": 2700.00,
        "amount_residual": 0.00,
        "state": "posted",
        "payment_state": "paid"
    },
    {
        "id": 103,
        "name": "INV/2026/00003",
        "move_type": "out_invoice",
        "partner_id": [3, "Global Services Ltd"],
        "invoice_date": "2026-02-05",
        "invoice_date_due": "2026-03-05",
        "amount_untaxed": 7500.00,
        "amount_tax": 600.00,
        "amount_total": 8100.00,
        "amount_residual": 8100.00,
        "state": "draft",
        "payment_state": "not_paid"
    }
]

MOCK_INVOICE_CREATE_SUCCESS = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": 104  # New invoice ID
}

MOCK_INVOICE_CREATE_VALIDATION_ERROR = {
    "jsonrpc": "2.0",
    "id": 1,
    "error": {
        "code": -32098,
        "message": "Validation Error",
        "data": {
            "name": "odoo.exceptions.ValidationError",
            "message": "Partner is required for customer invoices",
            "debug": "Traceback..."
        }
    }
}

MOCK_INVOICE_POST_SUCCESS = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": True
}


# =============================================================================
# Payment Responses
# =============================================================================

MOCK_PAYMENTS = [
    {
        "id": 201,
        "name": "PAY/2026/0001",
        "partner_id": [2, "TechStart Inc"],
        "amount": 2700.00,
        "payment_type": "inbound",
        "payment_method_line_id": [1, "Manual"],
        "date": "2026-02-04",
        "state": "posted",
        "ref": "Payment for INV/2026/00002"
    }
]

MOCK_PAYMENT_CREATE_SUCCESS = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": 202  # New payment ID
}


# =============================================================================
# Financial Summary Data
# =============================================================================

def get_mock_financial_summary(date_from: str, date_to: str) -> dict:
    """Generate mock financial summary for CEO briefing."""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "result": [
            {
                "id": 101,
                "name": "INV/2026/00001",
                "partner_id": [1, "Acme Corporation"],
                "amount_total": 5400.00,
                "amount_residual": 5400.00,
                "state": "posted",
                "invoice_date": "2026-02-01"
            },
            {
                "id": 102,
                "name": "INV/2026/00002",
                "partner_id": [2, "TechStart Inc"],
                "amount_total": 2700.00,
                "amount_residual": 0.00,
                "state": "posted",
                "invoice_date": "2026-02-03"
            }
        ]
    }


MOCK_REVENUE_BY_CUSTOMER = {
    "Acme Corporation": 5400.00,
    "TechStart Inc": 2700.00,
    "Global Services Ltd": 0.00  # Draft invoice not counted
}

MOCK_TOTAL_REVENUE = 8100.00
MOCK_TOTAL_RECEIVABLE = 5400.00


# =============================================================================
# Error Responses
# =============================================================================

MOCK_CONNECTION_TIMEOUT = {
    "error": "Connection timeout after 30 seconds"
}

MOCK_SERVER_ERROR = {
    "jsonrpc": "2.0",
    "id": 1,
    "error": {
        "code": -32500,
        "message": "Server Error",
        "data": {
            "name": "odoo.exceptions.ServerError",
            "message": "Internal server error",
            "debug": "Traceback..."
        }
    }
}

MOCK_PERMISSION_DENIED = {
    "jsonrpc": "2.0",
    "id": 1,
    "error": {
        "code": -32097,
        "message": "Access Denied",
        "data": {
            "name": "odoo.exceptions.AccessDenied",
            "message": "You don't have permission to access this record"
        }
    }
}


# =============================================================================
# Mock API Client
# =============================================================================

class MockOdooClient:
    """Mock Odoo client for testing."""

    def __init__(self, should_fail: bool = False, fail_count: int = 0):
        """
        Initialize mock client.

        Args:
            should_fail: If True, all calls will fail
            fail_count: Number of times to fail before succeeding (for retry testing)
        """
        self.should_fail = should_fail
        self.fail_count = fail_count
        self._call_count = 0
        self.calls: list[dict] = []

    def authenticate(self, db: str, username: str, password: str) -> int | None:
        """Mock authentication."""
        self.calls.append({
            "method": "authenticate",
            "args": {"db": db, "username": username}
        })

        if self.should_fail:
            return None
        return 2  # User ID

    def call(self, model: str, method: str, args: list, kwargs: dict | None = None) -> Any:
        """Mock model method call."""
        self._call_count += 1
        self.calls.append({
            "method": f"{model}.{method}",
            "args": args,
            "kwargs": kwargs
        })

        if self._call_count <= self.fail_count:
            raise ConnectionError("Connection timeout")

        if self.should_fail:
            raise ConnectionError("Connection failed")

        # Return appropriate mock data based on model and method
        if model == "account.move":
            if method == "create":
                return 104
            elif method == "search_read":
                return MOCK_INVOICES
            elif method == "action_post":
                return True
        elif model == "account.payment":
            if method == "create":
                return 202
            elif method == "search_read":
                return MOCK_PAYMENTS
            elif method == "action_post":
                return True
        elif model == "res.partner":
            if method == "search":
                return [p["id"] for p in MOCK_PARTNERS]
            elif method == "read":
                return MOCK_PARTNERS
            elif method == "search_read":
                return MOCK_PARTNERS

        return None

    def reset(self):
        """Reset call tracking."""
        self._call_count = 0
        self.calls = []


# =============================================================================
# Test Data Generators
# =============================================================================

def generate_invoice_data(
    partner_id: int = 1,
    partner_name: str = "Test Customer",
    amount: float = 1000.00,
    date_str: str | None = None
) -> dict:
    """Generate test invoice data."""
    if date_str is None:
        date_str = date.today().isoformat()

    return {
        "move_type": "out_invoice",
        "partner_id": partner_id,
        "invoice_date": date_str,
        "invoice_line_ids": [
            (0, 0, {
                "name": "Consulting Services",
                "quantity": 1,
                "price_unit": amount
            })
        ]
    }


def generate_payment_data(
    partner_id: int = 1,
    amount: float = 1000.00,
    payment_type: str = "inbound",
    date_str: str | None = None
) -> dict:
    """Generate test payment data."""
    if date_str is None:
        date_str = date.today().isoformat()

    return {
        "partner_id": partner_id,
        "amount": amount,
        "payment_type": payment_type,
        "date": date_str,
        "journal_id": 1  # Default bank journal
    }


# =============================================================================
# Fixtures for pytest
# =============================================================================

def pytest_fixtures():
    """Return fixtures for pytest."""
    return {
        "mock_odoo_client": MockOdooClient(),
        "mock_failing_client": MockOdooClient(should_fail=True),
        "mock_retry_client": MockOdooClient(fail_count=2),
        "mock_partners": MOCK_PARTNERS,
        "mock_invoices": MOCK_INVOICES,
        "mock_payments": MOCK_PAYMENTS
    }
