"""Tests for classification routes."""

import pytest
from unittest.mock import patch
import json


@pytest.mark.unit
class TestClassifyEndpoint:
    """Tests for email classification endpoint."""

    @patch('classifier.classify_email')
    def test_classify_success(self, mock_classify, client):
        """Test successful email classification."""
        mock_classify.return_value = {
            "label": "PHISHING",
            "confidence": 0.95,
            "reasoning": "Email attempts credential theft",
            "latency_ms": 1234.5,
            "tokens_used": 450
        }

        response = client.post(
            "/api/v1/classify",
            json={"email_text": "This is a suspicious email trying to steal credentials"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["label"] == "PHISHING"
        assert data["confidence"] == 0.95

    def test_classify_empty_email(self, client):
        """Test classification with empty email."""
        response = client.post(
            "/api/v1/classify",
            json={"email_text": ""}
        )
        assert response.status_code == 400

    def test_classify_whitespace_only(self, client):
        """Test classification with whitespace-only email."""
        response = client.post(
            "/api/v1/classify",
            json={"email_text": "   "}
        )
        assert response.status_code == 400

    def test_classify_too_short(self, client):
        """Test classification with email too short."""
        response = client.post(
            "/api/v1/classify",
            json={"email_text": "short"}
        )
        assert response.status_code == 422

    @patch('classifier.classify_email')
    def test_classify_with_gmail_id(self, mock_classify, client):
        """Test classification with Gmail message ID."""
        mock_classify.return_value = {
            "label": "LEGITIMATE",
            "confidence": 0.92,
            "reasoning": "Valid business email",
            "latency_ms": 1000.0,
            "tokens_used": 400
        }

        response = client.post(
            "/api/v1/classify",
            json={
                "email_text": "This is a legitimate business email with important information",
                "gmail_message_id": "abc123xyz"
            }
        )
        assert response.status_code == 200
        mock_classify.assert_called_once()
        assert mock_classify.call_args[1]["gmail_message_id"] == "abc123xyz"

    @patch('classifier.classify_email')
    def test_classify_authenticated_user(self, mock_classify, client, auth_headers):
        """Test classification by authenticated user."""
        mock_classify.return_value = {
            "label": "SPAM",
            "confidence": 0.88,
            "reasoning": "Marketing email",
            "latency_ms": 900.0,
            "tokens_used": 350
        }

        response = client.post(
            "/api/v1/classify",
            json={"email_text": "Buy cheap products now! Click here for huge discounts!"},
            headers=auth_headers
        )
        assert response.status_code == 200


@pytest.mark.unit
class TestBatchClassifyEndpoint:
    """Tests for batch email classification endpoint."""

    @patch('classifier.classify_email')
    def test_batch_classify_success(self, mock_classify, client):
        """Test successful batch classification."""
        mock_classify.side_effect = [
            {
                "label": "PHISHING",
                "confidence": 0.95,
                "reasoning": "Email 1 is phishing",
                "latency_ms": 1200.0,
                "tokens_used": 450
            },
            {
                "label": "LEGITIMATE",
                "confidence": 0.92,
                "reasoning": "Email 2 is legitimate",
                "latency_ms": 1100.0,
                "tokens_used": 400
            }
        ]

        response = client.post(
            "/api/v1/classify-batch",
            json={
                "emails": [
                    "Suspicious email 1",
                    "Legitimate email 2"
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["results"]) == 2
        assert data["results"][0]["success"] is True
        assert data["results"][1]["success"] is True

    def test_batch_classify_empty(self, client):
        """Test batch classification with empty list."""
        response = client.post(
            "/api/v1/classify-batch",
            json={"emails": []}
        )
        assert response.status_code == 400

    def test_batch_classify_too_many(self, client):
        """Test batch classification exceeding max limit."""
        response = client.post(
            "/api/v1/classify-batch",
            json={
                "emails": ["email"] * 51
            }
        )
        assert response.status_code == 400
        assert "Maximum 50 emails" in response.json()["detail"]

    @patch('classifier.classify_email')
    def test_batch_classify_partial_failure(self, mock_classify, client):
        """Test batch classification with partial failures."""
        mock_classify.side_effect = [
            {
                "label": "PHISHING",
                "confidence": 0.95,
                "reasoning": "Email 1 is phishing",
                "latency_ms": 1200.0,
                "tokens_used": 450
            },
            Exception("API error"),
            {
                "label": "SPAM",
                "confidence": 0.88,
                "reasoning": "Email 3 is spam",
                "latency_ms": 1100.0,
                "tokens_used": 400
            }
        ]

        response = client.post(
            "/api/v1/classify-batch",
            json={
                "emails": [
                    "Email 1",
                    "Email 2 (will fail)",
                    "Email 3"
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["results"][0]["success"] is True
        assert data["results"][1]["success"] is False
        assert data["results"][2]["success"] is True

    def test_batch_classify_max_size(self, client):
        """Test batch classification at max size (50)."""
        with patch('classifier.classify_email') as mock_classify:
            mock_classify.return_value = {
                "label": "LEGITIMATE",
                "confidence": 0.9,
                "reasoning": "OK",
                "latency_ms": 1000.0,
                "tokens_used": 400
            }

            response = client.post(
                "/api/v1/classify-batch",
                json={
                    "emails": ["email"] * 50
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 50


@pytest.mark.unit
class TestParseEmailEndpoint:
    """Tests for email parsing endpoint."""

    def test_parse_email_success(self, client):
        """Test successful email parsing."""
        email_text = """From: sender@example.com
To: recipient@example.com
Subject: Test Email
Date: Mon, 01 Jan 2024 10:00:00 +0000

This is the email body."""

        response = client.post(
            "/api/v1/parse-email",
            json={"email_text": email_text}
        )
        assert response.status_code == 200
        data = response.json()
        assert "headers" in data
        assert "body" in data
        assert "is_html" in data
        assert "extracted_addresses" in data

    def test_parse_email_empty(self, client):
        """Test parsing empty email."""
        response = client.post(
            "/api/v1/parse-email",
            json={"email_text": ""}
        )
        assert response.status_code == 400

    def test_parse_email_with_html(self, client):
        """Test parsing HTML email."""
        email_text = """From: sender@example.com
To: recipient@example.com
Subject: HTML Email

<html><body><h1>Test</h1></body></html>"""

        response = client.post(
            "/api/v1/parse-email",
            json={"email_text": email_text}
        )
        assert response.status_code == 200
        data = response.json()
        assert "sender@example.com" in data["extracted_addresses"]
        assert "recipient@example.com" in data["extracted_addresses"]
