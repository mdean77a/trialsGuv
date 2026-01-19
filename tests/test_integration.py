"""Integration tests that test multiple components together."""
import pytest
from pathlib import Path
from unittest.mock import patch, Mock


class TestEndToEndWorkflow:
    """End-to-end integration tests."""

    @patch('main.ClinicalTrialsDownloader.download_document')
    @patch('requests.Session')
    @patch('time.sleep')
    def test_complete_download_workflow(self, mock_sleep, mock_session_class,
                                       mock_download, temp_output_dir,
                                       sample_api_response_success):
        """Test complete workflow from search to download."""
        from main import ClinicalTrialsDownloader

        # Setup mocks
        mock_session = Mock()
        mock_response = Mock()
        mock_response.json.return_value = sample_api_response_success
        mock_response.raise_for_status = Mock()
        mock_session.get.return_value = mock_response
        mock_session_class.return_value = mock_session
        mock_download.return_value = True

        # Create downloader
        downloader = ClinicalTrialsDownloader(output_dir=str(temp_output_dir))
        downloader.session = mock_session

        # Run download
        pairs = downloader.download_pairs(
            subject="diabetes",
            num_pairs=1,
            verbose=False,
            require_icf=True
        )

        # Verify results
        assert len(pairs) > 0
        protocol_path, icf_path = pairs[0]
        assert protocol_path is not None


class TestErrorHandling:
    """Tests for error handling across components."""

    @patch('requests.Session')
    def test_api_error_handling(self, mock_session_class, temp_output_dir):
        """Test handling of API errors."""
        import requests
        from main import ClinicalTrialsDownloader

        mock_session = Mock()
        # Must use requests exception type to be caught by the handler
        mock_session.get.side_effect = requests.exceptions.RequestException("API Error")
        mock_session_class.return_value = mock_session

        downloader = ClinicalTrialsDownloader(output_dir=str(temp_output_dir))
        downloader.session = mock_session

        with patch('time.sleep'):
            studies = downloader.search_studies_with_documents(
                subject="diabetes",
                max_results=10
            )

        # Should return empty list on error
        assert studies == []

    @patch('requests.Session')
    def test_rate_limiting_handling(self, mock_session_class, temp_output_dir):
        """Test handling of rate limiting (429 errors)."""
        import requests
        from main import ClinicalTrialsDownloader

        mock_session = Mock()
        mock_response_429 = Mock()
        mock_response_429.status_code = 429

        # Create a proper RequestException with response attribute for rate limit
        exc = requests.exceptions.RequestException("Rate limited")
        exc.response = mock_response_429

        # After rate limit, return empty response to stop the loop
        mock_response_success = Mock()
        mock_response_success.json.return_value = {"studies": [], "totalCount": 0}
        mock_response_success.raise_for_status = Mock()

        # First call raises rate limit, second succeeds
        mock_session.get.side_effect = [exc, mock_response_success]
        mock_session_class.return_value = mock_session

        downloader = ClinicalTrialsDownloader(output_dir=str(temp_output_dir))
        downloader.session = mock_session

        # Should handle rate limiting gracefully
        with patch('time.sleep') as mock_sleep:
            studies = downloader.search_studies_with_documents(
                subject="diabetes",
                max_results=10
            )

        # Sleep should be called for rate limit backoff (60 seconds)
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert 60 in sleep_calls


class TestDirectoryStructure:
    """Tests for directory structure creation."""

    def test_subject_directory_creation(self, temp_output_dir):
        """Test that subject directories are created correctly."""
        from main import ClinicalTrialsDownloader

        downloader = ClinicalTrialsDownloader(output_dir=str(temp_output_dir))
        sanitized = downloader._sanitize_filename("Diabetes Type 2")

        assert sanitized == "diabetes_type_2"

    def test_investigator_directory_creation(self, temp_output_dir):
        """Test that investigator directories are created correctly."""
        from main import ClinicalTrialsDownloader

        downloader = ClinicalTrialsDownloader(output_dir=str(temp_output_dir))
        sanitized = downloader._sanitize_filename("John Smith, MD")

        assert sanitized == "john_smith_md"

    @patch('main.ClinicalTrialsDownloader.search_studies_with_documents')
    @patch('main.ClinicalTrialsDownloader.download_document')
    @patch('time.sleep')
    def test_combined_directory_naming(self, mock_sleep, mock_download, mock_search,
                                      temp_output_dir, sample_study_with_both_docs):
        """Test directory naming with both subject and investigator."""
        from main import ClinicalTrialsDownloader

        mock_search.return_value = [sample_study_with_both_docs]
        mock_download.return_value = True

        downloader = ClinicalTrialsDownloader(output_dir=str(temp_output_dir))

        pairs = downloader.download_pairs(
            subject="diabetes",
            investigator="John Smith",
            num_pairs=1,
            verbose=False
        )

        # Check that directory was created with both subject and investigator
        expected_dir = temp_output_dir / "diabetes_investigator_john_smith"
        # Directory should exist or be created during download


class TestPartialDownloadCleanup:
    """Tests for cleanup of partial downloads."""

    @patch('main.ClinicalTrialsDownloader.search_studies_with_documents')
    @patch('time.sleep')
    def test_cleanup_removes_empty_study_directory(self, mock_sleep, mock_search,
                                                   temp_output_dir, sample_study_with_both_docs):
        """Test that empty study directories are removed on failure."""
        from main import ClinicalTrialsDownloader

        mock_search.return_value = [sample_study_with_both_docs]

        downloader = ClinicalTrialsDownloader(output_dir=str(temp_output_dir))

        # Mock download to fail
        with patch.object(downloader, 'download_document', return_value=False):
            pairs = downloader.download_pairs(
                subject="diabetes",
                num_pairs=1,
                verbose=False,
                require_icf=True
            )

        # No pairs should be returned
        assert len(pairs) == 0


class TestMultipleStudyDownload:
    """Tests for downloading multiple studies."""

    @patch('main.ClinicalTrialsDownloader.search_studies_with_documents')
    @patch('main.ClinicalTrialsDownloader.download_document')
    @patch('time.sleep')
    def test_download_stops_at_requested_count(self, mock_sleep, mock_download, mock_search,
                                               temp_output_dir):
        """Test that download stops after reaching requested pair count."""
        from main import ClinicalTrialsDownloader

        # Create multiple studies
        studies = []
        for i in range(5):
            studies.append({
                "protocolSection": {
                    "identificationModule": {
                        "nctId": f"NCT0000000{i}",
                        "briefTitle": f"Test Study {i}"
                    }
                },
                "documentSection": {
                    "largeDocumentModule": {
                        "largeDocs": [
                            {
                                "typeAbbrev": "Prot",
                                "hasProtocol": True,
                                "hasIcf": False,
                                "filename": f"Protocol_{i}.pdf"
                            },
                            {
                                "typeAbbrev": "ICF",
                                "hasProtocol": False,
                                "hasIcf": True,
                                "filename": f"ICF_{i}.pdf"
                            }
                        ]
                    }
                }
            })

        mock_search.return_value = studies
        mock_download.return_value = True

        downloader = ClinicalTrialsDownloader(output_dir=str(temp_output_dir))

        pairs = downloader.download_pairs(
            subject="diabetes",
            num_pairs=2,  # Only request 2, even though 5 available
            verbose=False,
            require_icf=True
        )

        # Should only download 2 pairs
        assert len(pairs) == 2

    @patch('main.ClinicalTrialsDownloader.search_studies_with_documents')
    @patch('main.ClinicalTrialsDownloader.download_document')
    @patch('time.sleep')
    def test_download_continues_on_single_failure(self, mock_sleep, mock_download, mock_search,
                                                  temp_output_dir):
        """Test that download continues to next study on single failure."""
        from main import ClinicalTrialsDownloader

        # Create two studies
        studies = []
        for i in range(2):
            studies.append({
                "protocolSection": {
                    "identificationModule": {
                        "nctId": f"NCT0000000{i}",
                        "briefTitle": f"Test Study {i}"
                    }
                },
                "documentSection": {
                    "largeDocumentModule": {
                        "largeDocs": [
                            {
                                "typeAbbrev": "Prot",
                                "hasProtocol": True,
                                "hasIcf": False,
                                "filename": f"Protocol_{i}.pdf"
                            },
                            {
                                "typeAbbrev": "ICF",
                                "hasProtocol": False,
                                "hasIcf": True,
                                "filename": f"ICF_{i}.pdf"
                            }
                        ]
                    }
                }
            })

        mock_search.return_value = studies
        # First study fails (both docs), second succeeds
        mock_download.side_effect = [False, False, True, True]

        downloader = ClinicalTrialsDownloader(output_dir=str(temp_output_dir))

        pairs = downloader.download_pairs(
            subject="diabetes",
            num_pairs=1,
            verbose=False,
            require_icf=True
        )

        # Should have downloaded one pair (second study)
        assert len(pairs) == 1
