# Pi-hole Sentinel Test Suite

This directory contains unit and integration tests for the Pi-hole Sentinel project.

## Quick Start

### Install Test Dependencies

```bash
# Create virtual environment (if not already created)
python3 -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -r requirements-dev.txt
```

### Run All Tests

```bash
# Run all tests with coverage
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_validation.py

# Run specific test class
pytest tests/test_validation.py::TestIPValidation

# Run specific test function
pytest tests/test_validation.py::TestIPValidation::test_valid_ipv4_addresses
```

## Test Organization

### Test Files

- **`test_validation.py`** - Input validation function tests
  - IP address validation
  - Network interface name validation
  - Port number validation
  - Username validation
  - Security injection prevention

- **`test_vip_detection.py`** - VIP detection logic tests
  - MAC address extraction
  - VIP location determination
  - Retry logic
  - ARP table parsing

- **`test_api_handlers.py`** - API request/response tests
  - Pi-hole authentication
  - Stats parsing
  - DHCP config parsing
  - Error handling
  - Session management

- **`test_dhcp_parsing.py`** - DHCP configuration tests
  - Config structure parsing
  - State determination
  - Misconfiguration detection
  - Failover scenarios

### Test Categories

Tests are marked with categories for selective execution:

- **`@pytest.mark.unit`** - Fast unit tests (no external dependencies)
- **`@pytest.mark.integration`** - Integration tests (may require external services)
- **`@pytest.mark.slow`** - Slow-running tests
- **`@pytest.mark.network`** - Tests requiring network access
- **`@pytest.mark.asyncio`** - Async tests

### Run Tests by Category

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# Run async tests
pytest -m asyncio
```

## Coverage Reports

### Generate Coverage Report

```bash
# Run tests with coverage
pytest --cov=dashboard --cov=setup --cov-report=html

# Open HTML coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Coverage Goals

- **Current Target:** 60%+ code coverage
- **Long-term Goal:** 80%+ code coverage

### View Coverage in Terminal

```bash
# Show missing lines
pytest --cov=dashboard --cov=setup --cov-report=term-missing
```

## Continuous Integration

Tests are automatically run on every push via GitHub Actions (see `.github/workflows/code-quality.yml`).

### CI Test Command

```bash
# Same command used in CI
pytest --cov=dashboard --cov=setup --cov-report=xml --cov-fail-under=60
```

## Writing Tests

### Test Naming Conventions

- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

### Example Test Structure

```python
import pytest

class TestFeatureName:
    """Tests for feature X."""

    @pytest.fixture
    def sample_data(self):
        """Provide test data."""
        return {"key": "value"}

    def test_normal_case(self, sample_data):
        """Test normal operation."""
        result = function_under_test(sample_data)
        assert result == expected_value

    def test_edge_case(self):
        """Test edge case."""
        result = function_under_test(edge_case_input)
        assert result == expected_edge_result

    def test_error_handling(self):
        """Test error handling."""
        with pytest.raises(ExpectedError):
            function_under_test(invalid_input)
```

### Async Test Example

```python
import pytest

class TestAsyncFunction:
    """Tests for async functions."""

    @pytest.mark.asyncio
    async def test_async_operation(self):
        """Test async operation."""
        result = await async_function()
        assert result == expected_value
```

## Fixtures

Common test fixtures are defined in `conftest.py`:

- **`sample_config`** - Sample configuration dictionary
- **`sample_network_config`** - Sample network configuration
- **`http_session`** - aiohttp ClientSession for async tests
- **`mock_env_vars`** - Mock environment variables
- **`mock_pihole_auth_response`** - Mock Pi-hole auth response
- **`mock_pihole_stats_response`** - Mock Pi-hole stats response
- **`mock_dhcp_config_enabled`** - Mock DHCP config (enabled)
- **`mock_dhcp_config_disabled`** - Mock DHCP config (disabled)

### Using Fixtures

```python
def test_with_fixture(sample_config):
    """Test using fixture."""
    assert sample_config["primary_ip"] == "10.10.100.10"
```

## Mocking

### Mock External Calls

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_with_mock():
    """Test with mocked external call."""
    with patch('module.external_function', new=AsyncMock(return_value="mocked")):
        result = await function_that_calls_external()
        assert result == "mocked"
```

## Test Data

Test data files (JSON, YAML, etc.) should be placed in `tests/data/`.

## Debugging Tests

### Run with Debugger

```bash
# Run with Python debugger
pytest --pdb

# Drop into debugger on first failure
pytest -x --pdb
```

### Show Print Statements

```bash
# Show print() output
pytest -s

# Show print() and logs
pytest -s --log-cli-level=DEBUG
```

### Run Specific Test with Verbose Output

```bash
pytest -vv tests/test_validation.py::TestIPValidation::test_valid_ipv4_addresses
```

## Performance Testing

### Show Test Duration

```bash
# Show slowest 10 tests
pytest --durations=10

# Show all test durations
pytest --durations=0
```

## Troubleshooting

### Import Errors

If you get import errors:

```bash
# Ensure you're in the project root
cd /path/to/pihole-sentinel

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements-dev.txt
```

### Module Not Found

If tests can't find project modules:

```python
# Add to top of test file
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
```

### Async Test Errors

If async tests fail with "no running event loop":

```python
# Mark test with @pytest.mark.asyncio
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result == expected
```

## Best Practices

1. **Write tests first** - TDD approach when adding new features
2. **Test edge cases** - Don't just test happy path
3. **Test error handling** - Ensure errors are caught and handled
4. **Keep tests independent** - Each test should be runnable alone
5. **Use descriptive names** - Test names should describe what they test
6. **Mock external dependencies** - Don't rely on external services
7. **Aim for fast tests** - Unit tests should run in milliseconds
8. **Update tests with code** - Keep tests synchronized with code changes

## Resources

- **pytest documentation:** https://docs.pytest.org/
- **pytest-asyncio documentation:** https://pytest-asyncio.readthedocs.io/
- **pytest-cov documentation:** https://pytest-cov.readthedocs.io/
- **Python unittest.mock:** https://docs.python.org/3/library/unittest.mock.html

## Contributing

When contributing tests:

1. Run full test suite before committing
2. Ensure coverage doesn't decrease
3. Add tests for all new features
4. Add tests for all bug fixes
5. Update this README if adding new test categories
