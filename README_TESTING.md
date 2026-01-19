# Testing Guide

## Overview

This test suite provides comprehensive coverage for the ClinicalTrials.gov Document Downloader application. It includes unit tests, integration tests, and fixtures to support refactoring with confidence.

## Test Structure

```
tests/
├── __init__.py                 # Test package initialization
├── conftest.py                 # Pytest fixtures and configuration
├── test_dataclasses.py        # Tests for DocumentInfo and StudyDocuments
├── test_downloader.py         # Tests for ClinicalTrialsDownloader class
├── test_manifest.py           # Tests for manifest creation
├── test_cli.py                # Tests for CLI argument parsing
└── test_integration.py        # Integration and end-to-end tests
```

## Running Tests

### Install Test Dependencies

```bash
# Install project with test dependencies
uv sync --extra test
```

Or install test dependencies individually:
```bash
uv pip install pytest pytest-cov pytest-mock requests-mock
```

### Run All Tests

```bash
uv run pytest
```

### Run Specific Test Files

```bash
# Unit tests for dataclasses
uv run pytest tests/test_dataclasses.py

# Downloader tests
uv run pytest tests/test_downloader.py

# Integration tests
uv run pytest tests/test_integration.py
```

### Run Tests by Category

```bash
# Run only unit tests
uv run pytest -m unit

# Run only integration tests
uv run pytest -m integration
```

### Run with Coverage Report

```bash
uv run pytest --cov=main --cov-report=html --cov-report=term
```

This generates an HTML coverage report in `htmlcov/index.html`.

### Run Specific Test

```bash
uv run pytest tests/test_downloader.py::TestExtractDocumentInfo::test_extract_both_documents
```

### Run with Verbose Output

```bash
uv run pytest -v
```

### Run with Print Statements

```bash
uv run pytest -s
```

## Test Categories

### Unit Tests

Test individual functions and methods in isolation:
- **test_dataclasses.py**: Tests for `DocumentInfo` and `StudyDocuments` dataclasses
- **test_downloader.py**: Tests for individual methods of `ClinicalTrialsDownloader`
- **test_manifest.py**: Tests for `create_manifest()` function

### Integration Tests

Test multiple components working together:
- **test_integration.py**: End-to-end workflows, error handling, directory structure

### CLI Tests

Test command-line interface:
- **test_cli.py**: Argument parsing, validation, main function behavior

## Key Test Fixtures

Defined in `conftest.py`:

- `sample_study_with_both_docs`: Mock study with protocol and ICF
- `sample_study_protocol_only`: Mock study with protocol only
- `sample_study_no_docs`: Mock study with no documents
- `sample_api_response_success`: Mock API response with studies
- `temp_output_dir`: Temporary directory for test file operations
- `mock_requests_session`: Mock HTTP session for API calls

## Writing New Tests

### Example Unit Test

```python
def test_new_feature(temp_output_dir):
    """Test description."""
    downloader = ClinicalTrialsDownloader(output_dir=str(temp_output_dir))
    
    result = downloader.some_method()
    
    assert result == expected_value
```

### Example Integration Test with Mocking

```python
@patch('main.ClinicalTrialsDownloader.download_document')
@patch('time.sleep')
def test_workflow(mock_sleep, mock_download, sample_study_with_both_docs):
    """Test complete workflow."""
    mock_download.return_value = True
    
    # Test code here
    
    assert result is not None
```

## Mocking External Dependencies

The test suite mocks external dependencies to ensure tests are:
- **Fast**: No actual network calls
- **Reliable**: No dependency on external services
- **Isolated**: Tests don't affect real data

Mocked components:
- HTTP requests (`requests.Session`)
- File downloads
- API responses
- Time delays (`time.sleep`)

## Coverage Goals

Target coverage: **≥ 90%**

Check current coverage:
```bash
uv run pytest --cov=main --cov-report=term-missing
```

## Continuous Integration

To add CI/CD, create `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      - name: Install dependencies
        run: uv sync
      - name: Run tests
        run: uv run pytest --cov=main --cov-report=xml
```

## Troubleshooting

### Import Errors

If you get import errors, ensure you're running from the project root:
```bash
cd /path/to/trialsgov
uv run pytest
```

### Mock Not Working

Ensure the patch path matches the actual import path in the module:
```python
# If main.py does: import requests
@patch('main.requests.Session')  # Correct

# If main.py does: from requests import Session
@patch('requests.Session')  # Correct
```

### Tests Passing Locally But Failing in CI

- Check Python version consistency
- Verify all dependencies are in requirements-test.txt
- Check for hardcoded paths or timing assumptions

## Best Practices

1. **Test one thing per test**: Each test should verify a single behavior
2. **Use descriptive names**: Test names should describe what they test
3. **Arrange-Act-Assert**: Structure tests clearly
4. **Mock external dependencies**: Keep tests fast and isolated
5. **Use fixtures**: Avoid code duplication with shared fixtures
6. **Test edge cases**: Include tests for error conditions
7. **Keep tests maintainable**: Tests should be easy to understand and modify

## Future Enhancements

Potential additions:
- Property-based testing with `hypothesis`
- Performance benchmarks with `pytest-benchmark`
- Parameterized tests for multiple scenarios
- Snapshot testing for complex outputs
- Load testing for concurrent downloads
