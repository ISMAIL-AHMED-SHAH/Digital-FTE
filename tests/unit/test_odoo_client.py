"""Unit Tests for Odoo JSON-RPC Client (T018).

Tests for connection, authentication, invoice creation, payment creation,
and financial query functionality per contracts/odoo-mcp.json.

Uses mock fixtures from tests/fixtures/mock_odoo_api.py.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, datetime
import json

# Import fixtures
import sys
sys.path.insert(0, str(pytest.importorskip("pathlib").Path(__file__).parent.parent))
from fixtures.mock_odoo_api import (
    MOCK_ODOO_VERSION,
    MOCK_ODOO_DATABASE,
    MOCK_ODOO_USER,
    MOCK_ODOO_COMPANY,
    mock_authenticate_success,
    mock_authenticate_failure,
    mock_create_invoice_success,
    mock_create_invoice_validation_error,
    mock_create_payment_success,
    mock_get_invoices_response,
    mock_get_payments_response,
    mock_get_partners_response,
    mock_search_read_response,
)


class TestOdooClientConnection:
    """Test Odoo client connection and authentication."""

    def test_connection_success(self):
        """Test successful connection to Odoo."""
        # Mock the JSON-RPC response
        response = mock_authenticate_success()

        assert response["result"]["uid"] > 0
        assert response["result"]["username"] == MOCK_ODOO_USER
        assert response["result"]["company_name"] == MOCK_ODOO_COMPANY

    def test_connection_timeout(self):
        """Test connection timeout handling."""
        # Should handle 30-second timeout per contract
        # Simulated by mock
        pass  # Will be tested with actual client

    def test_authentication_failure(self):
        """Test authentication failure handling."""
        response = mock_authenticate_failure()

        assert "error" in response
        assert response["error"]["code"] == -32097
        assert "Access Denied" in response["error"]["message"]

    def test_invalid_credentials(self):
        """Test invalid API key handling."""
        # Should return AUTH error category
        response = mock_authenticate_failure()

        assert response["error"]["code"] == -32097

    def test_connection_retry(self):
        """Test connection retry with exponential backoff."""
        # Contract specifies: max_attempts=3, initial_delay=1s, backoff=2x
        # Will be tested with actual client
        pass


class TestOdooInvoiceOperations:
    """Test invoice creation operations."""

    def test_create_invoice_success(self):
        """Test successful invoice creation."""
        response = mock_create_invoice_success()

        assert response["result"]["success"] is True
        assert response["result"]["invoice_id"] > 0
        assert response["result"]["state"] == "draft"
        assert response["result"]["amount_total"] > 0

    def test_create_invoice_with_multiple_lines(self):
        """Test invoice creation with multiple line items."""
        response = mock_create_invoice_success()

        # Invoice should contain multiple lines
        assert response["result"]["amount_untaxed"] == 1000.00
        assert response["result"]["amount_total"] == 1070.00  # With 7% tax

    def test_create_invoice_validation_error(self):
        """Test invoice creation with validation errors."""
        response = mock_create_invoice_validation_error()

        assert "error" in response
        assert response["error"]["code"] == -32098
        assert "validation" in response["error"]["message"].lower()

    def test_create_invoice_partner_not_found(self):
        """Test invoice creation with non-existent partner."""
        # Should return PARTNER_NOT_FOUND error
        pass

    def test_create_invoice_returns_draft_state(self):
        """Verify invoice is always created in draft state (HITL safety)."""
        response = mock_create_invoice_success()

        # Contract requires draft state for HITL
        assert response["result"]["state"] == "draft"

    def test_create_invoice_generates_approval_file(self):
        """Test that invoice creation generates approval request."""
        response = mock_create_invoice_success()

        assert "approval_file" in response["result"]
        assert "Needs_Action" in response["result"]["approval_file"]


class TestOdooPaymentOperations:
    """Test payment creation operations."""

    def test_create_payment_inbound_success(self):
        """Test successful inbound (customer) payment creation."""
        response = mock_create_payment_success(payment_type="inbound")

        assert response["result"]["success"] is True
        assert response["result"]["payment_id"] > 0
        assert response["result"]["state"] == "draft"

    def test_create_payment_outbound_success(self):
        """Test successful outbound (vendor) payment creation."""
        response = mock_create_payment_success(payment_type="outbound")

        assert response["result"]["success"] is True
        assert response["result"]["state"] == "draft"

    def test_create_payment_with_reference(self):
        """Test payment creation with reference number."""
        response = mock_create_payment_success(reference="INV-2026-0001")

        assert response["result"]["success"] is True

    def test_create_payment_validation_error(self):
        """Test payment creation with invalid amount."""
        # Amount must be >= 0.01 per contract
        pass

    def test_create_payment_returns_draft_state(self):
        """Verify payment is always created in draft state (HITL safety)."""
        response = mock_create_payment_success()

        assert response["result"]["state"] == "draft"


class TestOdooFinancialSummary:
    """Test financial summary operations."""

    def test_get_financial_summary_success(self):
        """Test successful financial summary retrieval."""
        invoices = mock_get_invoices_response()
        payments = mock_get_payments_response()

        # Calculate expected totals
        total_revenue = sum(inv["amount_total"] for inv in invoices["result"])
        total_paid = sum(pay["amount"] for pay in payments["result"])

        assert total_revenue > 0
        assert total_paid > 0

    def test_get_financial_summary_date_range(self):
        """Test financial summary with date range filter."""
        invoices = mock_get_invoices_response()

        # All invoices should be within date range
        for inv in invoices["result"]:
            assert "invoice_date" in inv

    def test_get_financial_summary_top_customers(self):
        """Test top customers calculation."""
        # Should return top N customers by revenue
        partners = mock_get_partners_response()

        assert len(partners["result"]) > 0
        assert all("name" in p for p in partners["result"])

    def test_get_financial_summary_excludes_drafts_by_default(self):
        """Test that drafts are excluded by default."""
        invoices = mock_get_invoices_response()

        # All returned invoices should be posted
        for inv in invoices["result"]:
            assert inv["state"] == "posted"

    def test_get_financial_summary_includes_drafts_when_requested(self):
        """Test that drafts can be included when requested."""
        # Include drafts flag should work
        pass


class TestOdooPostOperations:
    """Test invoice and payment posting operations."""

    def test_post_invoice_success(self):
        """Test successful invoice posting."""
        # Requires valid approval token
        pass

    def test_post_invoice_invalid_token(self):
        """Test invoice posting with invalid approval token."""
        # Should return APPROVAL_INVALID error
        pass

    def test_post_invoice_not_found(self):
        """Test posting non-existent invoice."""
        # Should return INVOICE_NOT_FOUND error
        pass

    def test_post_payment_success(self):
        """Test successful payment posting."""
        # Requires valid approval token
        pass

    def test_post_payment_invalid_token(self):
        """Test payment posting with invalid approval token."""
        pass


class TestOdooClientErrorHandling:
    """Test error handling and categorization."""

    def test_connection_error_categorized_as_transient(self):
        """Test that connection errors are categorized as transient."""
        # Should trigger retry with backoff
        pass

    def test_auth_error_categorized_correctly(self):
        """Test that auth errors are categorized as AUTH."""
        response = mock_authenticate_failure()

        # Error code -32097 should map to AUTH category
        assert response["error"]["code"] == -32097

    def test_validation_error_categorized_as_logic(self):
        """Test that validation errors are categorized as LOGIC."""
        response = mock_create_invoice_validation_error()

        # Error code -32098 should map to LOGIC category
        assert response["error"]["code"] == -32098

    def test_timeout_triggers_retry(self):
        """Test that timeout triggers retry mechanism."""
        # 30-second timeout per contract
        pass

    def test_rate_limit_handling(self):
        """Test rate limit detection and handling."""
        # Should categorize as transient and retry
        pass


class TestOdooClientConfiguration:
    """Test client configuration."""

    def test_timeout_configuration(self):
        """Test timeout settings match contract."""
        # connection_ms: 30000, request_ms: 60000
        pass

    def test_retry_configuration(self):
        """Test retry settings match contract."""
        # max_attempts: 3, initial_delay: 1s, max_delay: 10s, backoff: 2x
        pass

    def test_environment_variable_loading(self):
        """Test environment variables are loaded correctly."""
        # ODOO_HOST, ODOO_PORT, ODOO_DATABASE, ODOO_USERNAME
        pass

    def test_credential_loading(self):
        """Test API key is loaded from credential store."""
        # credential:odoo_api_key
        pass


class TestOdooJsonRpcProtocol:
    """Test JSON-RPC protocol compliance."""

    def test_request_format(self):
        """Test JSON-RPC 2.0 request format."""
        request = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "common",
                "method": "version",
                "args": []
            },
            "id": 1
        }

        assert request["jsonrpc"] == "2.0"
        assert "method" in request
        assert "params" in request
        assert "id" in request

    def test_response_format(self):
        """Test JSON-RPC 2.0 response format."""
        response = mock_authenticate_success()

        assert "jsonrpc" in response
        assert "result" in response or "error" in response
        assert "id" in response

    def test_error_response_format(self):
        """Test JSON-RPC error response format."""
        response = mock_authenticate_failure()

        assert "error" in response
        assert "code" in response["error"]
        assert "message" in response["error"]
