# Testing Guide

## Running Tests

### Install test dependencies
```bash
pip install -r requirements.txt
```

### Run all tests
```bash
pytest
```

### Run with coverage
```bash
pytest --cov=. --cov-report=html
```

### Run specific test file
```bash
pytest tests/test_classifier.py
```

### Run tests by marker
```bash
pytest -m unit
pytest -m integration
```

### Run tests in verbose mode
```bash
pytest -v
```

## Test Structure

```
tests/
├── conftest.py              # Pytest fixtures and configuration
├── test_auth_routes.py      # Authentication endpoint tests
├── test_classify_routes.py  # Classification endpoint tests
└── test_classifier.py       # Classifier logic tests
```

## Test Categories

### Unit Tests
- Test individual functions and classes
- Marked with `@pytest.mark.unit`
- Should be fast and isolated

### Integration Tests
- Test interactions between components
- Marked with `@pytest.mark.integration`
- May use real database

## Writing New Tests

### Basic Test Structure
```python
import pytest
from unittest.mock import patch

@pytest.mark.unit
class TestMyFeature:
    """Test suite for my feature."""
    
    def test_something(self, client):
        """Test description."""
        response = client.get("/endpoint")
        assert response.status_code == 200
```

### Using Fixtures
- `client` - FastAPI test client
- `db_session` - Test database session
- `test_user` - Pre-created test user
- `admin_user` - Pre-created admin user
- `auth_headers` - Authorization headers for test_user
- `admin_headers` - Authorization headers for admin_user

### Mocking External Calls
```python
from unittest.mock import patch

@patch('classifier.classify_email')
def test_endpoint(self, mock_classify, client):
    mock_classify.return_value = {
        "label": "PHISHING",
        "confidence": 0.95,
        "reasoning": "..."
    }
    # Test code here
```

## Test Coverage

Target coverage: 80%+

View coverage report:
```bash
pytest --cov=. --cov-report=html
open htmlcov/index.html
```

## Common Issues

### Database locks
If tests fail with database locks:
- Ensure previous test processes aren't running
- Delete `test.db` if it exists
- Run tests sequentially (default behavior)

### Import errors
- Ensure backend directory is in PYTHONPATH
- Run tests from project root: `pytest`

### Async test failures
- Use `@pytest.mark.asyncio` decorator
- Ensure `pytest-asyncio` is installed

## CI/CD Integration

Tests run automatically on:
- Pre-commit hooks (configure in `.pre-commit-config.yaml`)
- GitHub Actions (configure in `.github/workflows/`)
- Local development with `pytest-watch`

```bash
# Install pytest-watch
pip install pytest-watch

# Run tests on file changes
ptw
```

## Performance Benchmarks

Key endpoints performance targets:
- Classification: < 2 seconds
- Batch (50 emails): < 90 seconds
- Metrics: < 100ms
- History: < 200ms

Run performance tests:
```bash
pytest -k "performance" -v
```
