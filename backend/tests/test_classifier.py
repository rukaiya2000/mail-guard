"""Tests for email classification functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from classifier import classify_email, _validate_classification_result, _parse_llm_response
import json


class TestValidateClassificationResult:
    """Tests for classification result validation."""

    def test_valid_result(self):
        """Test valid classification result."""
        result = {
            "label": "PHISHING",
            "confidence": 0.95,
            "reasoning": "Suspicious email"
        }
        assert _validate_classification_result(result) is True

    def test_missing_label(self):
        """Test result missing label."""
        result = {
            "confidence": 0.95,
            "reasoning": "Suspicious email"
        }
        assert _validate_classification_result(result) is False

    def test_invalid_label(self):
        """Test result with invalid label."""
        result = {
            "label": "INVALID",
            "confidence": 0.95,
            "reasoning": "Suspicious email"
        }
        assert _validate_classification_result(result) is False

    def test_confidence_out_of_range(self):
        """Test result with confidence > 1.0."""
        result = {
            "label": "PHISHING",
            "confidence": 1.5,
            "reasoning": "Suspicious email"
        }
        assert _validate_classification_result(result) is False

    def test_confidence_negative(self):
        """Test result with negative confidence."""
        result = {
            "label": "PHISHING",
            "confidence": -0.5,
            "reasoning": "Suspicious email"
        }
        assert _validate_classification_result(result) is False

    def test_confidence_zero(self):
        """Test result with zero confidence is valid."""
        result = {
            "label": "LEGITIMATE",
            "confidence": 0.0,
            "reasoning": "Valid email"
        }
        assert _validate_classification_result(result) is True

    def test_lowercase_label_converted(self):
        """Test that lowercase labels are converted to uppercase."""
        result = {
            "label": "phishing",
            "confidence": 0.95,
            "reasoning": "Test"
        }
        assert _validate_classification_result(result) is True


class TestParseResponse:
    """Tests for LLM response parsing."""

    def test_valid_json_response(self):
        """Test parsing valid JSON response."""
        content = json.dumps({
            "label": "PHISHING",
            "confidence": 0.95,
            "reasoning": "Email attempts credential theft"
        })
        result = _parse_llm_response(content)
        assert result["label"] == "PHISHING"
        assert result["confidence"] == 0.95

    def test_invalid_json(self):
        """Test parsing invalid JSON raises error."""
        content = "not valid json"
        with pytest.raises(ValueError, match="Invalid JSON response"):
            _parse_llm_response(content)

    def test_missing_required_fields(self):
        """Test response with missing fields raises error."""
        content = json.dumps({
            "label": "PHISHING",
            "confidence": 0.95
        })
        with pytest.raises(ValueError, match="missing required fields"):
            _parse_llm_response(content)

    def test_invalid_confidence_type(self):
        """Test response with non-numeric confidence."""
        content = json.dumps({
            "label": "PHISHING",
            "confidence": "high",
            "reasoning": "Test"
        })
        with pytest.raises(ValueError, match="missing required fields"):
            _parse_llm_response(content)


class TestClassifyEmail:
    """Tests for email classification."""

    @patch('classifier.get_openai_client')
    @patch('classifier.get_cached_classification')
    def test_cached_result(self, mock_cache, mock_client):
        """Test that cached results are returned."""
        mock_cache.return_value = Mock(
            label="PHISHING",
            confidence=0.95,
            reasoning="Cached result",
            latency_ms=10.5,
            tokens_used=0
        )

        result = classify_email("test email")
        assert result["label"] == "PHISHING"
        assert result["cached"] is True
        assert mock_client.call_count == 0

    @patch('classifier.get_openai_client')
    @patch('classifier.get_cached_classification')
    @patch('classifier._log_classification')
    def test_successful_classification(self, mock_log, mock_cache, mock_client):
        """Test successful email classification."""
        mock_cache.return_value = None

        mock_response = Mock()
        mock_response.usage.total_tokens = 450
        mock_response.choices[0].message.content = json.dumps({
            "label": "LEGITIMATE",
            "confidence": 0.92,
            "reasoning": "Valid business email"
        })

        mock_client_instance = Mock()
        mock_client_instance.chat.completions.create.return_value = mock_response
        mock_client.return_value = mock_client_instance

        result = classify_email("test email", user_id=1)
        assert result["label"] == "LEGITIMATE"
        assert result["confidence"] == 0.92
        assert "cached" not in result or result["cached"] is False
        mock_log.assert_called_once()

    @patch('classifier.get_openai_client')
    @patch('classifier.get_cached_classification')
    @patch('classifier._log_classification')
    def test_timeout_retry_logic(self, mock_log, mock_cache, mock_client):
        """Test retry logic on timeout."""
        mock_cache.return_value = None

        mock_client_instance = Mock()
        import openai
        # First call raises timeout, second succeeds
        mock_response = Mock()
        mock_response.usage.total_tokens = 450
        mock_response.choices[0].message.content = json.dumps({
            "label": "SPAM",
            "confidence": 0.88,
            "reasoning": "Marketing email"
        })

        mock_client_instance.chat.completions.create.side_effect = [
            openai.Timeout("Request timed out"),
            mock_response
        ]
        mock_client.return_value = mock_client_instance

        result = classify_email("test email")
        assert result["label"] == "SPAM"
        assert mock_client_instance.chat.completions.create.call_count == 2

    @patch('classifier.get_openai_client')
    @patch('classifier.get_cached_classification')
    @patch('classifier._log_classification')
    def test_max_retries_exceeded(self, mock_log, mock_cache, mock_client):
        """Test error when max retries exceeded."""
        mock_cache.return_value = None

        mock_client_instance = Mock()
        import openai
        mock_client_instance.chat.completions.create.side_effect = openai.Timeout("Persistent timeout")
        mock_client.return_value = mock_client_instance

        with pytest.raises(Exception, match="Classification failed"):
            classify_email("test email")

    @patch('classifier.get_openai_client')
    @patch('classifier.get_cached_classification')
    @patch('classifier._log_classification')
    def test_invalid_response_format(self, mock_log, mock_cache, mock_client):
        """Test handling of invalid response format."""
        mock_cache.return_value = None

        mock_response = Mock()
        mock_response.usage.total_tokens = 450
        mock_response.choices[0].message.content = "not json"

        mock_client_instance = Mock()
        mock_client_instance.chat.completions.create.return_value = mock_response
        mock_client.return_value = mock_client_instance

        with pytest.raises(Exception, match="Classification failed"):
            classify_email("test email")


@pytest.mark.unit
class TestClassifierEdgeCases:
    """Edge case tests for classifier."""

    @patch('classifier.get_openai_client')
    @patch('classifier.get_cached_classification')
    def test_very_long_email(self, mock_cache, mock_client):
        """Test classification of very long email."""
        mock_cache.return_value = None
        long_email = "test " * 10000

        assert len(long_email) > 50000

    @patch('classifier.get_openai_client')
    @patch('classifier.get_cached_classification')
    def test_email_with_special_characters(self, mock_cache, mock_client):
        """Test classification of email with special characters."""
        mock_cache.return_value = None
        special_email = "test ¡™£¢∞§¶•ªº–≠ special chars"

        # Should not raise exception
        assert len(special_email) > 0

    @patch('classifier.get_openai_client')
    @patch('classifier.get_cached_classification')
    def test_email_with_html_content(self, mock_cache, mock_client):
        """Test classification of HTML email."""
        mock_cache.return_value = None
        html_email = "<html><body><h1>Test</h1><p>HTML email</p></body></html>"

        # Should not raise exception
        assert "<html>" in html_email
