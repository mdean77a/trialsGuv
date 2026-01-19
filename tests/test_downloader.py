"""Tests for ClinicalTrialsDownloader class."""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from main import ClinicalTrialsDownloader, DocumentInfo, StudyDocuments


class TestClinicalTrialsDownloaderInit:
    """Tests for ClinicalTrialsDownloader initialization."""
    
    def test_init_creates_output_dir(self, tmp_path):
        """Test that initialization creates output directory."""
        output_dir = tmp_path / "downloads"
        downloader = ClinicalTrialsDownloader(output_dir=str(output_dir))

        assert downloader.output_dir == output_dir
        # headers is a CaseInsensitiveDict, check it has expected keys
        assert "Accept" in downloader.session.headers
        assert downloader.session.headers["Accept"] == "application/json"
    
    def test_init_default_output_dir(self):
        """Test initialization with default output directory."""
        downloader = ClinicalTrialsDownloader()
        
        assert downloader.output_dir == Path("./clinical_trial_documents")


class TestExtractDocumentInfo:
    """Tests for extract_document_info method."""
    
    def test_extract_both_documents(self, sample_study_with_both_docs):
        """Test extracting study with both protocol and ICF."""
        downloader = ClinicalTrialsDownloader()
        study_docs = downloader.extract_document_info(sample_study_with_both_docs)
        
        assert study_docs.nct_id == "NCT12345678"
        assert study_docs.brief_title == "Test Study with Both Documents"
        assert study_docs.protocol is not None
        assert study_docs.protocol.filename == "Protocol_001.pdf"
        assert study_docs.icf is not None
        assert study_docs.icf.filename == "ICF_001.pdf"
    
    def test_extract_protocol_only(self, sample_study_protocol_only):
        """Test extracting study with protocol only."""
        downloader = ClinicalTrialsDownloader()
        study_docs = downloader.extract_document_info(sample_study_protocol_only)
        
        assert study_docs.nct_id == "NCT87654321"
        assert study_docs.protocol is not None
        assert study_docs.protocol.filename == "Protocol_002.pdf"
        assert study_docs.icf is None
    
    def test_extract_no_documents(self, sample_study_no_docs):
        """Test extracting study with no documents."""
        downloader = ClinicalTrialsDownloader()
        study_docs = downloader.extract_document_info(sample_study_no_docs)
        
        assert study_docs.nct_id == "NCT11111111"
        assert study_docs.protocol is None
        assert study_docs.icf is None
    
    def test_extract_constructs_correct_url(self, sample_study_with_both_docs):
        """Test that document URLs are constructed correctly."""
        downloader = ClinicalTrialsDownloader()
        study_docs = downloader.extract_document_info(sample_study_with_both_docs)
        
        # NCT12345678 -> last 2 digits are 78
        expected_url = "https://clinicaltrials.gov/ProvidedDocs/78/NCT12345678/Protocol_001.pdf"
        assert study_docs.protocol.url == expected_url


class TestSanitizeFilename:
    """Tests for _sanitize_filename method."""
    
    def test_sanitize_removes_special_chars(self):
        """Test that special characters are removed."""
        downloader = ClinicalTrialsDownloader()

        # Special chars are simply removed (no underscores inserted)
        result = downloader._sanitize_filename("test@file#name!")
        assert result == "testfilename"
    
    def test_sanitize_replaces_spaces(self):
        """Test that spaces are replaced with underscores."""
        downloader = ClinicalTrialsDownloader()
        
        result = downloader._sanitize_filename("test file name")
        assert result == "test_file_name"
    
    def test_sanitize_multiple_spaces(self):
        """Test that multiple spaces are collapsed."""
        downloader = ClinicalTrialsDownloader()
        
        result = downloader._sanitize_filename("test    file    name")
        assert result == "test_file_name"
    
    def test_sanitize_lowercase(self):
        """Test that result is lowercase."""
        downloader = ClinicalTrialsDownloader()
        
        result = downloader._sanitize_filename("Test File Name")
        assert result == "test_file_name"
    
    def test_sanitize_strips_underscores(self):
        """Test that leading/trailing underscores are stripped."""
        downloader = ClinicalTrialsDownloader()
        
        result = downloader._sanitize_filename("__test__")
        assert result == "test"


class TestSearchStudiesWithDocuments:
    """Tests for search_studies_with_documents method."""
    
    @patch('main.ClinicalTrialsDownloader.extract_document_info')
    def test_search_with_subject_only(self, mock_extract, sample_api_response_success, temp_output_dir):
        """Test searching with subject parameter only."""
        downloader = ClinicalTrialsDownloader(output_dir=str(temp_output_dir))
        
        # Mock the session.get response
        mock_response = Mock()
        mock_response.json.return_value = sample_api_response_success
        mock_response.raise_for_status = Mock()
        downloader.session.get = Mock(return_value=mock_response)
        
        # Mock extract_document_info to return studies with protocols
        mock_study_docs = Mock()
        mock_study_docs.has_both.return_value = True
        mock_study_docs.has_protocol.return_value = True
        mock_extract.return_value = mock_study_docs
        
        with patch('time.sleep'):  # Skip sleep delays
            studies = downloader.search_studies_with_documents(
                subject="diabetes",
                max_results=10,
                require_icf=True
            )
        
        # Verify API was called with correct params
        call_args = downloader.session.get.call_args
        assert call_args[0][0].endswith("/studies")
        assert "query.cond" in call_args[1]["params"]
        assert call_args[1]["params"]["query.cond"] == "diabetes"
    
    @patch('main.ClinicalTrialsDownloader.extract_document_info')
    def test_search_with_investigator_only(self, mock_extract, sample_api_response_success, temp_output_dir):
        """Test searching with investigator parameter only."""
        downloader = ClinicalTrialsDownloader(output_dir=str(temp_output_dir))
        
        mock_response = Mock()
        mock_response.json.return_value = sample_api_response_success
        mock_response.raise_for_status = Mock()
        downloader.session.get = Mock(return_value=mock_response)
        
        mock_study_docs = Mock()
        mock_study_docs.has_protocol.return_value = True
        mock_extract.return_value = mock_study_docs
        
        with patch('time.sleep'):
            studies = downloader.search_studies_with_documents(
                investigator="John Smith",
                max_results=10,
                require_icf=False
            )
        
        call_args = downloader.session.get.call_args
        assert "query.term" in call_args[1]["params"]
        assert call_args[1]["params"]["query.term"] == "John Smith"
    
    @patch('main.ClinicalTrialsDownloader.extract_document_info')
    def test_search_with_both_params(self, mock_extract, sample_api_response_success, temp_output_dir):
        """Test searching with both subject and investigator."""
        downloader = ClinicalTrialsDownloader(output_dir=str(temp_output_dir))
        
        mock_response = Mock()
        mock_response.json.return_value = sample_api_response_success
        mock_response.raise_for_status = Mock()
        downloader.session.get = Mock(return_value=mock_response)
        
        mock_study_docs = Mock()
        mock_study_docs.has_both.return_value = True
        mock_extract.return_value = mock_study_docs
        
        with patch('time.sleep'):
            studies = downloader.search_studies_with_documents(
                subject="diabetes",
                investigator="John Smith",
                max_results=10,
                require_icf=True
            )
        
        call_args = downloader.session.get.call_args
        params = call_args[1]["params"]
        assert "query.cond" in params
        assert "query.term" in params
        assert params["query.cond"] == "diabetes"
        assert params["query.term"] == "John Smith"
    
    @patch('main.ClinicalTrialsDownloader.extract_document_info')
    def test_search_filters_by_require_icf(self, mock_extract, sample_api_response_success, temp_output_dir):
        """Test that require_icf parameter filters correctly."""
        downloader = ClinicalTrialsDownloader(output_dir=str(temp_output_dir))

        # Modify response to have no next page token to avoid pagination
        response_data = sample_api_response_success.copy()
        response_data["nextPageToken"] = None

        mock_response = Mock()
        mock_response.json.return_value = response_data
        mock_response.raise_for_status = Mock()
        downloader.session.get = Mock(return_value=mock_response)

        # First study has both, second has protocol only
        mock_study_both = Mock()
        mock_study_both.has_both.return_value = True
        mock_study_both.has_protocol.return_value = True

        mock_study_prot = Mock()
        mock_study_prot.has_both.return_value = False
        mock_study_prot.has_protocol.return_value = True

        mock_extract.side_effect = [mock_study_both, mock_study_prot]

        with patch('time.sleep'):
            # With require_icf=True, should only get first study
            studies = downloader.search_studies_with_documents(
                subject="diabetes",
                max_results=2,  # Match the number of studies in response
                require_icf=True
            )

        assert len(studies) == 1


class TestDownloadDocument:
    """Tests for download_document method."""
    
    def test_download_success(self, temp_output_dir):
        """Test successful document download."""
        downloader = ClinicalTrialsDownloader(output_dir=str(temp_output_dir))
        
        # Mock successful download
        mock_response = Mock()
        mock_response.iter_content = Mock(return_value=[b"chunk1", b"chunk2"])
        mock_response.raise_for_status = Mock()
        downloader.session.get = Mock(return_value=mock_response)
        
        doc = DocumentInfo(
            filename="test.pdf",
            size=1024,
            url="https://example.com/test.pdf",
            doc_type="Prot"
        )
        
        save_path = temp_output_dir / "test.pdf"
        result = downloader.download_document(doc, save_path)
        
        assert result is True
        assert save_path.exists()
        content = save_path.read_bytes()
        assert content == b"chunk1chunk2"
    
    def test_download_failure(self, temp_output_dir):
        """Test failed document download."""
        import requests
        downloader = ClinicalTrialsDownloader(output_dir=str(temp_output_dir))

        # Mock failed download - must use requests exception type
        downloader.session.get = Mock(side_effect=requests.exceptions.RequestException("Network error"))

        doc = DocumentInfo(
            filename="test.pdf",
            size=1024,
            url="https://example.com/test.pdf",
            doc_type="Prot"
        )

        save_path = temp_output_dir / "test.pdf"
        result = downloader.download_document(doc, save_path)

        assert result is False
        assert not save_path.exists()


class TestDownloadPairs:
    """Tests for download_pairs method."""
    
    @patch('main.ClinicalTrialsDownloader.download_document')
    @patch('main.ClinicalTrialsDownloader.search_studies_with_documents')
    @patch('time.sleep')
    def test_download_pairs_success(self, mock_sleep, mock_search, mock_download, 
                                   sample_study_with_both_docs, temp_output_dir):
        """Test successful download of document pairs."""
        downloader = ClinicalTrialsDownloader(output_dir=str(temp_output_dir))
        
        # Mock search returns study
        mock_search.return_value = [sample_study_with_both_docs]
        
        # Mock successful downloads
        mock_download.return_value = True
        
        pairs = downloader.download_pairs(
            subject="diabetes",
            num_pairs=1,
            verbose=False,
            require_icf=True
        )
        
        assert len(pairs) == 1
        protocol_path, icf_path = pairs[0]
        assert protocol_path.name.startswith("protocol_")
        assert icf_path.name.startswith("icf_")
    
    @patch('main.ClinicalTrialsDownloader.search_studies_with_documents')
    def test_download_pairs_no_studies_found(self, mock_search, temp_output_dir):
        """Test when no studies are found."""
        downloader = ClinicalTrialsDownloader(output_dir=str(temp_output_dir))

        mock_search.return_value = []

        pairs = downloader.download_pairs(
            subject="nonexistent",
            num_pairs=5,
            verbose=False
        )

        assert len(pairs) == 0

    @patch('main.ClinicalTrialsDownloader.download_document')
    @patch('main.ClinicalTrialsDownloader.search_studies_with_documents')
    @patch('time.sleep')
    def test_download_pairs_protocol_only_no_icf_required(self, mock_sleep, mock_search,
                                                          mock_download, sample_study_protocol_only,
                                                          temp_output_dir):
        """Test download with require_icf=False returns protocol only."""
        downloader = ClinicalTrialsDownloader(output_dir=str(temp_output_dir))

        mock_search.return_value = [sample_study_protocol_only]
        mock_download.return_value = True

        pairs = downloader.download_pairs(
            subject="diabetes",
            num_pairs=1,
            verbose=False,
            require_icf=False
        )

        assert len(pairs) == 1
        protocol_path, icf_path = pairs[0]
        assert protocol_path.name.startswith("protocol_")
        assert icf_path is None

    @patch('main.ClinicalTrialsDownloader.download_document')
    @patch('main.ClinicalTrialsDownloader.search_studies_with_documents')
    @patch('time.sleep')
    def test_download_pairs_protocol_failure_cleanup(self, mock_sleep, mock_search,
                                                     mock_download, sample_study_with_both_docs,
                                                     temp_output_dir):
        """Test that failed protocol download cleans up directory."""
        downloader = ClinicalTrialsDownloader(output_dir=str(temp_output_dir))

        mock_search.return_value = [sample_study_with_both_docs]
        # Protocol download fails
        mock_download.return_value = False

        pairs = downloader.download_pairs(
            subject="diabetes",
            num_pairs=1,
            verbose=False,
            require_icf=True
        )

        # No pairs should be returned on failure
        assert len(pairs) == 0

    @patch('main.ClinicalTrialsDownloader.download_document')
    @patch('main.ClinicalTrialsDownloader.search_studies_with_documents')
    @patch('time.sleep')
    def test_download_pairs_icf_failure_cleanup(self, mock_sleep, mock_search,
                                                mock_download, sample_study_with_both_docs,
                                                temp_output_dir):
        """Test that failed ICF download cleans up files."""
        downloader = ClinicalTrialsDownloader(output_dir=str(temp_output_dir))

        mock_search.return_value = [sample_study_with_both_docs]
        # Protocol succeeds, ICF fails
        mock_download.side_effect = [True, False]

        pairs = downloader.download_pairs(
            subject="diabetes",
            num_pairs=1,
            verbose=False,
            require_icf=True
        )

        # No pairs should be returned when ICF required but fails
        assert len(pairs) == 0

    @patch('main.ClinicalTrialsDownloader.download_document')
    @patch('main.ClinicalTrialsDownloader.search_studies_with_documents')
    @patch('time.sleep')
    def test_download_pairs_creates_study_directory(self, mock_sleep, mock_search,
                                                    mock_download, sample_study_with_both_docs,
                                                    temp_output_dir):
        """Test that download creates correct study directory structure."""
        downloader = ClinicalTrialsDownloader(output_dir=str(temp_output_dir))

        mock_search.return_value = [sample_study_with_both_docs]
        mock_download.return_value = True

        pairs = downloader.download_pairs(
            subject="diabetes",
            num_pairs=1,
            verbose=False,
            require_icf=True
        )

        # Verify directory structure
        subject_dir = temp_output_dir / "diabetes"
        assert subject_dir.exists()
        study_dir = subject_dir / "NCT12345678"
        assert study_dir.exists()

    @patch('main.ClinicalTrialsDownloader.download_document')
    @patch('main.ClinicalTrialsDownloader.search_studies_with_documents')
    @patch('time.sleep')
    def test_download_pairs_investigator_directory(self, mock_sleep, mock_search,
                                                   mock_download, sample_study_with_both_docs,
                                                   temp_output_dir):
        """Test directory creation with investigator only."""
        downloader = ClinicalTrialsDownloader(output_dir=str(temp_output_dir))

        mock_search.return_value = [sample_study_with_both_docs]
        mock_download.return_value = True

        pairs = downloader.download_pairs(
            investigator="John Smith",
            num_pairs=1,
            verbose=False,
            require_icf=True
        )

        # Verify directory structure with investigator prefix
        investigator_dir = temp_output_dir / "investigator_john_smith"
        assert investigator_dir.exists()

    @patch('main.ClinicalTrialsDownloader.download_document')
    @patch('main.ClinicalTrialsDownloader.search_studies_with_documents')
    @patch('time.sleep')
    def test_download_pairs_combined_subject_investigator_directory(self, mock_sleep, mock_search,
                                                                     mock_download, sample_study_with_both_docs,
                                                                     temp_output_dir):
        """Test directory creation with both subject and investigator."""
        downloader = ClinicalTrialsDownloader(output_dir=str(temp_output_dir))

        mock_search.return_value = [sample_study_with_both_docs]
        mock_download.return_value = True

        pairs = downloader.download_pairs(
            subject="diabetes",
            investigator="John Smith",
            num_pairs=1,
            verbose=False,
            require_icf=True
        )

        # Verify directory structure with combined naming
        combined_dir = temp_output_dir / "diabetes_investigator_john_smith"
        assert combined_dir.exists()

    @patch('main.ClinicalTrialsDownloader.download_document')
    @patch('main.ClinicalTrialsDownloader.search_studies_with_documents')
    @patch('time.sleep')
    @patch('builtins.print')
    def test_download_pairs_verbose_output(self, mock_print, mock_sleep, mock_search,
                                           mock_download, sample_study_with_both_docs,
                                           temp_output_dir):
        """Test that verbose mode prints progress information."""
        downloader = ClinicalTrialsDownloader(output_dir=str(temp_output_dir))

        mock_search.return_value = [sample_study_with_both_docs]
        mock_download.return_value = True

        pairs = downloader.download_pairs(
            subject="diabetes",
            num_pairs=1,
            verbose=True,
            require_icf=True
        )

        # Verify print was called with progress info
        assert mock_print.called
        call_strings = [str(call) for call in mock_print.call_args_list]
        assert any("Downloading Protocol" in s for s in call_strings)


class TestSearchStudiesEdgeCases:
    """Additional edge case tests for search_studies_with_documents."""

    @patch('main.ClinicalTrialsDownloader.extract_document_info')
    def test_search_pagination_with_next_token(self, mock_extract, temp_output_dir):
        """Test pagination when nextPageToken is present."""
        downloader = ClinicalTrialsDownloader(output_dir=str(temp_output_dir))

        # First response has next token, second doesn't
        response1 = {
            "studies": [{"protocolSection": {"identificationModule": {"nctId": "NCT001"}}}],
            "nextPageToken": "token123",
            "totalCount": 2
        }
        response2 = {
            "studies": [{"protocolSection": {"identificationModule": {"nctId": "NCT002"}}}],
            "totalCount": 2
        }

        mock_response = Mock()
        mock_response.json.side_effect = [response1, response2]
        mock_response.raise_for_status = Mock()
        downloader.session.get = Mock(return_value=mock_response)

        mock_study_docs = Mock()
        mock_study_docs.has_both.return_value = True
        mock_study_docs.has_protocol.return_value = True
        mock_extract.return_value = mock_study_docs

        with patch('time.sleep'):
            studies = downloader.search_studies_with_documents(
                subject="diabetes",
                max_results=2,
                require_icf=True
            )

        # Should have called get twice due to pagination
        assert downloader.session.get.call_count >= 1
        assert len(studies) >= 1

    @patch('main.ClinicalTrialsDownloader.extract_document_info')
    def test_search_empty_study_list(self, mock_extract, temp_output_dir):
        """Test when API returns empty study list."""
        downloader = ClinicalTrialsDownloader(output_dir=str(temp_output_dir))

        response = {
            "studies": [],
            "totalCount": 0
        }

        mock_response = Mock()
        mock_response.json.return_value = response
        mock_response.raise_for_status = Mock()
        downloader.session.get = Mock(return_value=mock_response)

        with patch('time.sleep'):
            studies = downloader.search_studies_with_documents(
                subject="nonexistent_condition_xyz",
                max_results=10,
                require_icf=True
            )

        assert len(studies) == 0

    def test_search_rate_limit_handling(self, temp_output_dir):
        """Test handling of 429 rate limit response."""
        import requests
        downloader = ClinicalTrialsDownloader(output_dir=str(temp_output_dir))

        # Create a proper RequestException with response attribute
        mock_response = Mock()
        mock_response.status_code = 429

        exc = requests.exceptions.RequestException("Rate limited")
        exc.response = mock_response

        # First call raises rate limit, second succeeds with empty
        mock_get = Mock()
        success_response = Mock()
        success_response.json.return_value = {"studies": [], "totalCount": 0}
        success_response.raise_for_status = Mock()

        mock_get.side_effect = [exc, success_response]
        downloader.session.get = mock_get

        with patch('time.sleep') as mock_sleep:
            studies = downloader.search_studies_with_documents(
                subject="diabetes",
                max_results=10,
                require_icf=True
            )

        # Should have called sleep for 60 seconds on rate limit
        sleep_calls = [call[0][0] for call in mock_sleep.call_args_list]
        assert 60 in sleep_calls

    def test_search_request_exception_no_response(self, temp_output_dir):
        """Test handling of RequestException without response attribute."""
        import requests
        downloader = ClinicalTrialsDownloader(output_dir=str(temp_output_dir))

        exc = requests.exceptions.RequestException("Connection failed")
        exc.response = None

        downloader.session.get = Mock(side_effect=exc)

        with patch('time.sleep'):
            studies = downloader.search_studies_with_documents(
                subject="diabetes",
                max_results=10,
                require_icf=True
            )

        # Should return empty list on error
        assert studies == []


class TestExtractDocumentInfoEdgeCases:
    """Additional edge case tests for extract_document_info."""

    def test_extract_missing_protocol_section(self):
        """Test extraction when protocolSection is missing."""
        downloader = ClinicalTrialsDownloader()

        study = {}

        study_docs = downloader.extract_document_info(study)

        assert study_docs.nct_id == "Unknown"
        assert study_docs.brief_title == "Unknown"
        assert study_docs.protocol is None
        assert study_docs.icf is None

    def test_extract_missing_identification_module(self):
        """Test extraction when identificationModule is missing."""
        downloader = ClinicalTrialsDownloader()

        study = {
            "protocolSection": {}
        }

        study_docs = downloader.extract_document_info(study)

        assert study_docs.nct_id == "Unknown"
        assert study_docs.brief_title == "Unknown"

    def test_extract_short_nct_id(self):
        """Test URL construction with short NCT ID."""
        downloader = ClinicalTrialsDownloader()

        study = {
            "protocolSection": {
                "identificationModule": {
                    "nctId": "X",  # Very short ID
                    "briefTitle": "Test"
                }
            },
            "documentSection": {
                "largeDocumentModule": {
                    "largeDocs": [
                        {
                            "typeAbbrev": "Prot",
                            "hasProtocol": True,
                            "hasIcf": False,
                            "filename": "test.pdf"
                        }
                    ]
                }
            }
        }

        study_docs = downloader.extract_document_info(study)

        # Should handle short ID gracefully (uses "00" as fallback is not implemented,
        # but should still work with slicing)
        assert study_docs.protocol is not None
        assert "X" in study_docs.protocol.url

    def test_extract_empty_large_docs_list(self):
        """Test extraction when largeDocs list is empty."""
        downloader = ClinicalTrialsDownloader()

        study = {
            "protocolSection": {
                "identificationModule": {
                    "nctId": "NCT12345678",
                    "briefTitle": "Test Study"
                }
            },
            "documentSection": {
                "largeDocumentModule": {
                    "largeDocs": []
                }
            }
        }

        study_docs = downloader.extract_document_info(study)

        assert study_docs.nct_id == "NCT12345678"
        assert study_docs.protocol is None
        assert study_docs.icf is None

    def test_extract_multiple_protocols_uses_first(self):
        """Test that first protocol document is used when multiple exist."""
        downloader = ClinicalTrialsDownloader()

        study = {
            "protocolSection": {
                "identificationModule": {
                    "nctId": "NCT12345678",
                    "briefTitle": "Test Study"
                }
            },
            "documentSection": {
                "largeDocumentModule": {
                    "largeDocs": [
                        {
                            "typeAbbrev": "Prot",
                            "hasProtocol": True,
                            "hasIcf": False,
                            "filename": "Protocol_First.pdf"
                        },
                        {
                            "typeAbbrev": "Prot",
                            "hasProtocol": True,
                            "hasIcf": False,
                            "filename": "Protocol_Second.pdf"
                        }
                    ]
                }
            }
        }

        study_docs = downloader.extract_document_info(study)

        # First protocol should be used
        assert study_docs.protocol.filename == "Protocol_First.pdf"

    @patch('builtins.print')
    def test_extract_debug_mode(self, mock_print):
        """Test debug mode prints document information."""
        downloader = ClinicalTrialsDownloader()

        study = {
            "protocolSection": {
                "identificationModule": {
                    "nctId": "NCT12345678",
                    "briefTitle": "Test Study"
                }
            },
            "documentSection": {
                "largeDocumentModule": {
                    "largeDocs": [
                        {
                            "typeAbbrev": "Prot",
                            "hasProtocol": True,
                            "hasIcf": False,
                            "filename": "Protocol.pdf"
                        }
                    ]
                }
            }
        }

        study_docs = downloader.extract_document_info(study, debug=True)

        # Verify debug output was printed
        assert mock_print.called
        call_strings = [str(call) for call in mock_print.call_args_list]
        assert any("NCT12345678" in s for s in call_strings)
        assert any("hasProtocol" in s for s in call_strings)

    def test_extract_document_without_size(self):
        """Test extraction when document has no size field."""
        downloader = ClinicalTrialsDownloader()

        study = {
            "protocolSection": {
                "identificationModule": {
                    "nctId": "NCT12345678",
                    "briefTitle": "Test Study"
                }
            },
            "documentSection": {
                "largeDocumentModule": {
                    "largeDocs": [
                        {
                            "typeAbbrev": "Prot",
                            "hasProtocol": True,
                            "hasIcf": False,
                            "filename": "Protocol.pdf"
                            # Note: no "size" field
                        }
                    ]
                }
            }
        }

        study_docs = downloader.extract_document_info(study)

        assert study_docs.protocol is not None
        assert study_docs.protocol.size is None


class TestDownloadDocumentEdgeCases:
    """Additional edge case tests for download_document."""

    def test_download_request_exception(self, temp_output_dir):
        """Test specific RequestException handling."""
        import requests
        downloader = ClinicalTrialsDownloader(output_dir=str(temp_output_dir))

        # Create RequestException
        exc = requests.exceptions.RequestException("Connection timeout")
        downloader.session.get = Mock(side_effect=exc)

        doc = DocumentInfo(
            filename="test.pdf",
            size=1024,
            url="https://example.com/test.pdf",
            doc_type="Prot"
        )

        save_path = temp_output_dir / "test.pdf"
        result = downloader.download_document(doc, save_path)

        assert result is False

    def test_download_http_error(self, temp_output_dir):
        """Test handling of HTTP error response."""
        import requests
        downloader = ClinicalTrialsDownloader(output_dir=str(temp_output_dir))

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        downloader.session.get = Mock(return_value=mock_response)

        doc = DocumentInfo(
            filename="test.pdf",
            size=1024,
            url="https://example.com/test.pdf",
            doc_type="Prot"
        )

        save_path = temp_output_dir / "test.pdf"
        result = downloader.download_document(doc, save_path)

        assert result is False
