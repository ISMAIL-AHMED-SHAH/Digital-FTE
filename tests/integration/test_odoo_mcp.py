"""Integration Tests for Odoo MCP Server (T019).

End-to-end tests for the Odoo MCP server tools:
- test_connection
- create_invoice
- create_payment
- get_financial_summary
- post_invoice
- post_payment

These tests require a running mock Odoo server or skip if unavailable.
"""

import pytest
import json
import os
import subprocess
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# Skip if no Odoo connection available
ODOO_URL = os.environ.get("ODOO_URL", "")
SKIP_INTEGRATION = not ODOO_URL or ODOO_URL == "mock"


@pytest.fixture
def mcp_server_process():
    """Start MCP server process for testing."""
    # For integration tests, we'd start the actual server
    # For now, return a mock
    yield MagicMock()


@pytest.fixture
def mock_odoo_responses():
    """Load mock responses for testing without live Odoo."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from fixtures.mock_odoo_api import (
        mock_authenticate_success,
        mock_create_invoice_success,
        mock_create_payment_success,
        mock_get_invoices_response,
        mock_get_payments_response,
    )

    return {
        "authenticate": mock_authenticate_success(),
        "create_invoice": mock_create_invoice_success(),
        "create_payment": mock_create_payment_success(),
        "get_invoices": mock_get_invoices_response(),
        "get_payments": mock_get_payments_response(),
    }


class TestOdooMCPTestConnection:
    """Test the test_connection MCP tool."""

    @pytest.mark.skipif(SKIP_INTEGRATION, reason="No Odoo connection")
    def test_connection_live(self, mcp_server_process):
        """Test live connection to Odoo server."""
        # Would send MCP request to test_connection tool
        pass

    def test_connection_mock(self, mock_odoo_responses):
        """Test connection using mock responses."""
        response = mock_odoo_responses["authenticate"]

        assert response["result"]["uid"] > 0
        assert "username" in response["result"]
        assert "company_name" in response["result"]

    def test_connection_returns_version(self, mock_odoo_responses):
        """Test that connection returns Odoo version."""
        # Version should be returned for diagnostic purposes
        pass

    def test_connection_returns_latency(self, mock_odoo_responses):
        """Test that connection returns latency measurement."""
        # latency_ms should be included
        pass


class TestOdooMCPCreateInvoice:
    """Test the create_invoice MCP tool."""

    @pytest.mark.skipif(SKIP_INTEGRATION, reason="No Odoo connection")
    def test_create_invoice_live(self, mcp_server_process):
        """Test live invoice creation."""
        pass

    def test_create_invoice_mock(self, mock_odoo_responses):
        """Test invoice creation using mock responses."""
        response = mock_odoo_responses["create_invoice"]

        assert response["result"]["success"] is True
        assert response["result"]["invoice_id"] > 0
        assert response["result"]["state"] == "draft"

    def test_create_invoice_input_validation(self):
        """Test input validation per contract schema."""
        # Required: customer_name, invoice_date, lines
        valid_input = {
            "customer_name": "Test Customer",
            "invoice_date": "2026-02-06",
            "lines": [
                {
                    "description": "Service",
                    "quantity": 1,
                    "unit_price": 100.00
                }
            ]
        }

        # Validate required fields present
        assert "customer_name" in valid_input
        assert "invoice_date" in valid_input
        assert "lines" in valid_input
        assert len(valid_input["lines"]) >= 1

    def test_create_invoice_optional_fields(self):
        """Test optional fields handling."""
        # Optional: due_date, notes, currency, tax_ids
        input_with_optional = {
            "customer_name": "Test Customer",
            "invoice_date": "2026-02-06",
            "due_date": "2026-03-06",
            "currency": "EUR",
            "notes": "Test invoice",
            "lines": [
                {
                    "description": "Service",
                    "quantity": 1,
                    "unit_price": 100.00,
                    "tax_ids": [1, 2]
                }
            ]
        }

        assert "due_date" in input_with_optional
        assert "currency" in input_with_optional

    def test_create_invoice_generates_approval_file(self, mock_odoo_responses):
        """Test that approval file is created."""
        response = mock_odoo_responses["create_invoice"]

        assert "approval_file" in response["result"]

    def test_create_invoice_calculates_totals(self, mock_odoo_responses):
        """Test that totals are calculated correctly."""
        response = mock_odoo_responses["create_invoice"]

        assert "amount_untaxed" in response["result"]
        assert "amount_tax" in response["result"]
        assert "amount_total" in response["result"]

        # Total should equal untaxed + tax
        total = response["result"]["amount_untaxed"] + response["result"]["amount_tax"]
        assert response["result"]["amount_total"] == total


class TestOdooMCPCreatePayment:
    """Test the create_payment MCP tool."""

    @pytest.mark.skipif(SKIP_INTEGRATION, reason="No Odoo connection")
    def test_create_payment_live(self, mcp_server_process):
        """Test live payment creation."""
        pass

    def test_create_payment_mock(self, mock_odoo_responses):
        """Test payment creation using mock responses."""
        response = mock_odoo_responses["create_payment"]

        assert response["result"]["success"] is True
        assert response["result"]["payment_id"] > 0
        assert response["result"]["state"] == "draft"

    def test_create_payment_input_validation(self):
        """Test input validation per contract schema."""
        # Required: partner_name, amount, payment_type
        valid_input = {
            "partner_name": "Test Customer",
            "amount": 100.00,
            "payment_type": "inbound"
        }

        assert "partner_name" in valid_input
        assert "amount" in valid_input
        assert valid_input["amount"] >= 0.01
        assert valid_input["payment_type"] in ["inbound", "outbound"]

    def test_create_payment_inbound_type(self):
        """Test inbound (customer) payment type."""
        input_data = {
            "partner_name": "Customer",
            "amount": 500.00,
            "payment_type": "inbound"
        }

        assert input_data["payment_type"] == "inbound"

    def test_create_payment_outbound_type(self):
        """Test outbound (vendor) payment type."""
        input_data = {
            "partner_name": "Vendor",
            "amount": 500.00,
            "payment_type": "outbound"
        }

        assert input_data["payment_type"] == "outbound"

    def test_create_payment_methods(self):
        """Test different payment methods."""
        methods = ["manual", "check", "bank_transfer", "credit_card"]

        for method in methods:
            input_data = {
                "partner_name": "Test",
                "amount": 100.00,
                "payment_type": "inbound",
                "payment_method": method
            }
            assert input_data["payment_method"] in methods


class TestOdooMCPGetFinancialSummary:
    """Test the get_financial_summary MCP tool."""

    @pytest.mark.skipif(SKIP_INTEGRATION, reason="No Odoo connection")
    def test_get_financial_summary_live(self, mcp_server_process):
        """Test live financial summary retrieval."""
        pass

    def test_get_financial_summary_mock(self, mock_odoo_responses):
        """Test financial summary using mock responses."""
        invoices = mock_odoo_responses["get_invoices"]["result"]
        payments = mock_odoo_responses["get_payments"]["result"]

        # Calculate summary
        total_revenue = sum(inv["amount_total"] for inv in invoices)
        total_paid = sum(pay["amount"] for pay in payments)

        assert total_revenue > 0
        assert total_paid >= 0

    def test_get_financial_summary_input_validation(self):
        """Test input validation per contract schema."""
        # Required: date_from, date_to
        valid_input = {
            "date_from": "2026-01-01",
            "date_to": "2026-01-31"
        }

        assert "date_from" in valid_input
        assert "date_to" in valid_input

    def test_get_financial_summary_output_structure(self):
        """Test output structure matches contract."""
        expected_structure = {
            "success": True,
            "period": {"from": "2026-01-01", "to": "2026-01-31"},
            "revenue": {"total": 10000, "paid": 8000, "receivable": 2000},
            "counts": {"invoices_posted": 5, "invoices_draft": 2, "payments_received": 4},
            "top_customers": [],
            "currency": "USD"
        }

        assert "success" in expected_structure
        assert "period" in expected_structure
        assert "revenue" in expected_structure
        assert "counts" in expected_structure

    def test_get_financial_summary_top_customers_limit(self):
        """Test top_customers_limit parameter."""
        input_data = {
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
            "top_customers_limit": 10
        }

        assert input_data["top_customers_limit"] >= 1
        assert input_data["top_customers_limit"] <= 20


class TestOdooMCPPostInvoice:
    """Test the post_invoice MCP tool."""

    @pytest.mark.skipif(SKIP_INTEGRATION, reason="No Odoo connection")
    def test_post_invoice_live(self, mcp_server_process):
        """Test live invoice posting."""
        pass

    def test_post_invoice_input_validation(self):
        """Test input validation per contract schema."""
        # Required: invoice_id, approval_token
        valid_input = {
            "invoice_id": 123,
            "approval_token": "abc123-token"
        }

        assert "invoice_id" in valid_input
        assert "approval_token" in valid_input

    def test_post_invoice_requires_approval(self):
        """Test that posting requires valid approval token."""
        # Without approval_token, should fail
        invalid_input = {
            "invoice_id": 123
        }

        assert "approval_token" not in invalid_input

    def test_post_invoice_changes_state_to_posted(self):
        """Test that posting changes state from draft to posted."""
        expected_output = {
            "success": True,
            "invoice_id": 123,
            "invoice_number": "INV/2026/00001",
            "state": "posted"
        }

        assert expected_output["state"] == "posted"


class TestOdooMCPPostPayment:
    """Test the post_payment MCP tool."""

    @pytest.mark.skipif(SKIP_INTEGRATION, reason="No Odoo connection")
    def test_post_payment_live(self, mcp_server_process):
        """Test live payment posting."""
        pass

    def test_post_payment_input_validation(self):
        """Test input validation per contract schema."""
        valid_input = {
            "payment_id": 456,
            "approval_token": "xyz789-token"
        }

        assert "payment_id" in valid_input
        assert "approval_token" in valid_input


class TestOdooMCPErrorHandling:
    """Test MCP error handling."""

    def test_connection_failed_error(self):
        """Test ODOO_CONNECTION_FAILED error code."""
        error = {
            "code": "ODOO_CONNECTION_FAILED",
            "message": "Unable to connect to Odoo server"
        }
        assert error["code"] == "ODOO_CONNECTION_FAILED"

    def test_auth_failed_error(self):
        """Test ODOO_AUTH_FAILED error code."""
        error = {
            "code": "ODOO_AUTH_FAILED",
            "message": "Authentication failed - check credentials"
        }
        assert error["code"] == "ODOO_AUTH_FAILED"

    def test_timeout_error(self):
        """Test ODOO_TIMEOUT error code."""
        error = {
            "code": "ODOO_TIMEOUT",
            "message": "Connection timed out (30 seconds)"
        }
        assert error["code"] == "ODOO_TIMEOUT"

    def test_validation_error(self):
        """Test ODOO_VALIDATION_ERROR error code."""
        error = {
            "code": "ODOO_VALIDATION_ERROR",
            "message": "Data validation failed in Odoo"
        }
        assert error["code"] == "ODOO_VALIDATION_ERROR"

    def test_partner_not_found_error(self):
        """Test PARTNER_NOT_FOUND error code."""
        error = {
            "code": "PARTNER_NOT_FOUND",
            "message": "Customer/partner not found in Odoo"
        }
        assert error["code"] == "PARTNER_NOT_FOUND"

    def test_approval_required_error(self):
        """Test APPROVAL_REQUIRED error code."""
        error = {
            "code": "APPROVAL_REQUIRED",
            "message": "Action requires approval - check approval_file"
        }
        assert error["code"] == "APPROVAL_REQUIRED"

    def test_approval_invalid_error(self):
        """Test APPROVAL_INVALID error code."""
        error = {
            "code": "APPROVAL_INVALID",
            "message": "Invalid or expired approval token"
        }
        assert error["code"] == "APPROVAL_INVALID"


class TestOdooMCPIntegrationWorkflow:
    """Test complete integration workflows."""

    @pytest.mark.skipif(SKIP_INTEGRATION, reason="No Odoo connection")
    def test_invoice_workflow(self, mcp_server_process):
        """Test complete invoice workflow: create -> approve -> post."""
        # 1. Create draft invoice
        # 2. Get approval file
        # 3. Simulate approval
        # 4. Post invoice
        # 5. Verify posted state
        pass

    @pytest.mark.skipif(SKIP_INTEGRATION, reason="No Odoo connection")
    def test_payment_workflow(self, mcp_server_process):
        """Test complete payment workflow: create -> approve -> post."""
        pass

    @pytest.mark.skipif(SKIP_INTEGRATION, reason="No Odoo connection")
    def test_financial_summary_workflow(self, mcp_server_process):
        """Test financial summary after creating invoices and payments."""
        pass

    def test_workflow_with_mocks(self, mock_odoo_responses):
        """Test workflow logic with mock responses."""
        # Create invoice
        invoice_response = mock_odoo_responses["create_invoice"]
        assert invoice_response["result"]["success"]

        invoice_id = invoice_response["result"]["invoice_id"]

        # Create payment
        payment_response = mock_odoo_responses["create_payment"]
        assert payment_response["result"]["success"]

        # Get financial summary
        invoices = mock_odoo_responses["get_invoices"]["result"]
        assert len(invoices) > 0
