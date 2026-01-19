"""Pytest configuration and shared fixtures."""
import json
from pathlib import Path
from typing import Dict, Any
import pytest
from unittest.mock import Mock


@pytest.fixture
def sample_study_with_both_docs() -> Dict[str, Any]:
    """Sample study with both protocol and ICF documents."""
    return {
        "protocolSection": {
            "identificationModule": {
                "nctId": "NCT12345678",
                "briefTitle": "Test Study with Both Documents"
            }
        },
        "documentSection": {
            "largeDocumentModule": {
                "largeDocs": [
                    {
                        "typeAbbrev": "Prot_SAP",
                        "hasProtocol": True,
                        "hasSap": True,
                        "hasIcf": False,
                        "filename": "Protocol_001.pdf",
                        "size": 1024000
                    },
                    {
                        "typeAbbrev": "ICF",
                        "hasProtocol": False,
                        "hasSap": False,
                        "hasIcf": True,
                        "filename": "ICF_001.pdf",
                        "size": 512000
                    }
                ]
            }
        }
    }


@pytest.fixture
def sample_study_protocol_only() -> Dict[str, Any]:
    """Sample study with protocol only (no ICF)."""
    return {
        "protocolSection": {
            "identificationModule": {
                "nctId": "NCT87654321",
                "briefTitle": "Test Study with Protocol Only"
            }
        },
        "documentSection": {
            "largeDocumentModule": {
                "largeDocs": [
                    {
                        "typeAbbrev": "Prot",
                        "hasProtocol": True,
                        "hasSap": False,
                        "hasIcf": False,
                        "filename": "Protocol_002.pdf",
                        "size": 2048000
                    }
                ]
            }
        }
    }


@pytest.fixture
def sample_study_no_docs() -> Dict[str, Any]:
    """Sample study with no documents."""
    return {
        "protocolSection": {
            "identificationModule": {
                "nctId": "NCT11111111",
                "briefTitle": "Test Study with No Documents"
            }
        }
    }


@pytest.fixture
def sample_api_response_success(sample_study_with_both_docs, sample_study_protocol_only):
    """Sample successful API response with multiple studies."""
    return {
        "studies": [
            sample_study_with_both_docs,
            sample_study_protocol_only
        ],
        "nextPageToken": "token123",
        "totalCount": 100
    }


@pytest.fixture
def sample_api_response_no_more():
    """Sample API response with no more results."""
    return {
        "studies": [],
        "totalCount": 0
    }


@pytest.fixture
def mock_requests_session():
    """Mock requests session."""
    session = Mock()
    return session


@pytest.fixture
def temp_output_dir(tmp_path):
    """Temporary output directory for tests."""
    output_dir = tmp_path / "test_downloads"
    output_dir.mkdir()
    return output_dir
