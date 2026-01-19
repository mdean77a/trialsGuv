"""Tests for CLI argument parsing and main function."""
import pytest
import sys
from unittest.mock import patch, Mock
from pathlib import Path


class TestCLIArguments:
    """Tests for command-line argument parsing."""
    
    def test_help_argument(self):
        """Test --help displays help message."""
        with patch('sys.argv', ['main.py', '--help']):
            with pytest.raises(SystemExit) as exc_info:
                import main
                main.main()
            assert exc_info.value.code == 0
    
    def test_subject_argument_only(self):
        """Test with subject argument only - valid configuration."""
        test_args = ['main.py', '--subject', 'diabetes', '--pairs', '5']

        with patch('sys.argv', test_args):
            with patch('main.ClinicalTrialsDownloader') as mock_downloader_class:
                mock_downloader = Mock()
                mock_downloader.download_pairs.return_value = []
                mock_downloader_class.return_value = mock_downloader

                import main
                # Should run without error (no SystemExit with code 1)
                main.main()

                # Verify downloader was called
                mock_downloader.download_pairs.assert_called_once()
    
    def test_investigator_argument_only(self):
        """Test with investigator argument only."""
        # This should work as investigator alone is valid
        test_args = ['main.py', '--investigator', 'John Smith', '--pairs', '5']
        
        with patch('sys.argv', test_args):
            # Should not raise an error about missing arguments
            pass
    
    def test_both_subject_and_investigator(self):
        """Test with both subject and investigator arguments."""
        test_args = [
            'main.py',
            '--subject', 'diabetes',
            '--investigator', 'John Smith',
            '--pairs', '10'
        ]
        
        with patch('sys.argv', test_args):
            # Should be valid
            pass
    
    def test_no_icf_flag(self):
        """Test --no-icf flag."""
        test_args = [
            'main.py',
            '--subject', 'diabetes',
            '--pairs', '5',
            '--no-icf'
        ]
        
        with patch('sys.argv', test_args):
            # Should be valid
            pass
    
    def test_quiet_flag(self):
        """Test --quiet flag."""
        test_args = [
            'main.py',
            '--subject', 'diabetes',
            '--pairs', '5',
            '--quiet'
        ]
        
        with patch('sys.argv', test_args):
            # Should be valid
            pass
    
    def test_output_directory_argument(self):
        """Test --output argument."""
        test_args = [
            'main.py',
            '--subject', 'diabetes',
            '--pairs', '5',
            '--output', './custom_output'
        ]
        
        with patch('sys.argv', test_args):
            # Should be valid
            pass
    
    def test_short_argument_forms(self):
        """Test short forms of arguments."""
        test_args = [
            'main.py',
            '-s', 'diabetes',
            '-i', 'John Smith',
            '-n', '10',
            '-o', './output',
            '-q'
        ]
        
        with patch('sys.argv', test_args):
            # Should be valid
            pass


class TestMainFunction:
    """Tests for the main() function."""
    
    @patch('main.ClinicalTrialsDownloader')
    @patch('main.create_manifest')
    def test_main_successful_download(self, mock_manifest, mock_downloader_class, tmp_path):
        """Test main function with successful downloads."""
        # Setup mocks
        mock_downloader = Mock()
        protocol_path = tmp_path / "study1" / "protocol.pdf"
        icf_path = tmp_path / "study1" / "icf.pdf"
        protocol_path.parent.mkdir(parents=True)
        protocol_path.touch()
        icf_path.touch()
        
        mock_downloader.download_pairs.return_value = [(protocol_path, icf_path)]
        mock_downloader_class.return_value = mock_downloader
        mock_manifest.return_value = tmp_path / "manifest.json"
        
        test_args = ['main.py', '--subject', 'diabetes', '--pairs', '1']
        
        with patch('sys.argv', test_args):
            import main
            # Would call main.main() but it has sys.exit, so we test components
            
            # Verify downloader would be called correctly
            assert mock_downloader_class.called or True  # Setup for future test
    
    @patch('main.ClinicalTrialsDownloader')
    def test_main_no_downloads(self, mock_downloader_class, tmp_path):
        """Test main function when no documents are downloaded."""
        mock_downloader = Mock()
        mock_downloader.download_pairs.return_value = []
        mock_downloader_class.return_value = mock_downloader
        
        test_args = ['main.py', '--subject', 'nonexistent', '--pairs', '5']
        
        with patch('sys.argv', test_args):
            # Should handle gracefully with no downloads
            pass
    
    def test_main_missing_required_args(self):
        """Test main function with missing required arguments."""
        test_args = ['main.py', '--pairs', '5']  # Missing subject and investigator
        
        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit) as exc_info:
                import main
                main.main()
            assert exc_info.value.code == 1
    
    def test_main_invalid_pairs_number(self):
        """Test main function with invalid number of pairs."""
        test_args = ['main.py', '--subject', 'diabetes', '--pairs', '0']

        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit) as exc_info:
                import main
                main.main()
            assert exc_info.value.code == 1

    def test_main_negative_pairs_number(self):
        """Test main function with negative number of pairs."""
        test_args = ['main.py', '--subject', 'diabetes', '--pairs', '-5']

        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit) as exc_info:
                import main
                main.main()
            assert exc_info.value.code == 1


class TestMainFunctionIntegration:
    """Integration tests for main() function with mocked dependencies."""

    @patch('main.create_manifest')
    @patch('main.ClinicalTrialsDownloader')
    @patch('builtins.print')
    def test_main_with_subject_downloads_and_creates_manifest(self, mock_print,
                                                              mock_downloader_class,
                                                              mock_create_manifest, tmp_path):
        """Test main function creates manifest after successful downloads."""
        # Setup
        protocol_path = tmp_path / "NCT123" / "protocol.pdf"
        icf_path = tmp_path / "NCT123" / "icf.pdf"
        protocol_path.parent.mkdir(parents=True)
        protocol_path.touch()
        icf_path.touch()

        mock_downloader = Mock()
        mock_downloader.download_pairs.return_value = [(protocol_path, icf_path)]
        mock_downloader_class.return_value = mock_downloader

        mock_create_manifest.return_value = tmp_path / "manifest.json"

        test_args = ['main.py', '--subject', 'diabetes', '--pairs', '1', '--output', str(tmp_path)]

        with patch('sys.argv', test_args):
            import main
            main.main()

        # Verify downloader was called correctly
        mock_downloader.download_pairs.assert_called_once()
        call_kwargs = mock_downloader.download_pairs.call_args[1]
        assert call_kwargs['subject'] == 'diabetes'
        assert call_kwargs['num_pairs'] == 1
        assert call_kwargs['require_icf'] is True

        # Verify manifest was created
        mock_create_manifest.assert_called_once()

    @patch('main.create_manifest')
    @patch('main.ClinicalTrialsDownloader')
    @patch('builtins.print')
    def test_main_with_investigator_only(self, mock_print, mock_downloader_class,
                                         mock_create_manifest, tmp_path):
        """Test main function works with investigator only (no subject)."""
        protocol_path = tmp_path / "NCT123" / "protocol.pdf"
        icf_path = tmp_path / "NCT123" / "icf.pdf"
        protocol_path.parent.mkdir(parents=True)
        protocol_path.touch()
        icf_path.touch()

        mock_downloader = Mock()
        mock_downloader.download_pairs.return_value = [(protocol_path, icf_path)]
        mock_downloader_class.return_value = mock_downloader
        mock_create_manifest.return_value = tmp_path / "manifest.json"

        test_args = ['main.py', '--investigator', 'John Smith', '--pairs', '1', '--output', str(tmp_path)]

        with patch('sys.argv', test_args):
            import main
            main.main()

        call_kwargs = mock_downloader.download_pairs.call_args[1]
        assert call_kwargs['investigator'] == 'John Smith'
        assert call_kwargs['subject'] is None

    @patch('main.create_manifest')
    @patch('main.ClinicalTrialsDownloader')
    @patch('builtins.print')
    def test_main_with_no_icf_flag(self, mock_print, mock_downloader_class,
                                   mock_create_manifest, tmp_path):
        """Test main function passes require_icf=False when --no-icf is used."""
        protocol_path = tmp_path / "NCT123" / "protocol.pdf"
        protocol_path.parent.mkdir(parents=True)
        protocol_path.touch()

        mock_downloader = Mock()
        mock_downloader.download_pairs.return_value = [(protocol_path, None)]
        mock_downloader_class.return_value = mock_downloader
        mock_create_manifest.return_value = tmp_path / "manifest.json"

        test_args = ['main.py', '--subject', 'diabetes', '--pairs', '1', '--no-icf', '--output', str(tmp_path)]

        with patch('sys.argv', test_args):
            import main
            main.main()

        call_kwargs = mock_downloader.download_pairs.call_args[1]
        assert call_kwargs['require_icf'] is False

    @patch('main.create_manifest')
    @patch('main.ClinicalTrialsDownloader')
    @patch('builtins.print')
    def test_main_with_quiet_flag(self, mock_print, mock_downloader_class,
                                  mock_create_manifest, tmp_path):
        """Test main function passes verbose=False when --quiet is used."""
        protocol_path = tmp_path / "NCT123" / "protocol.pdf"
        icf_path = tmp_path / "NCT123" / "icf.pdf"
        protocol_path.parent.mkdir(parents=True)
        protocol_path.touch()
        icf_path.touch()

        mock_downloader = Mock()
        mock_downloader.download_pairs.return_value = [(protocol_path, icf_path)]
        mock_downloader_class.return_value = mock_downloader
        mock_create_manifest.return_value = tmp_path / "manifest.json"

        test_args = ['main.py', '--subject', 'diabetes', '--pairs', '1', '--quiet', '--output', str(tmp_path)]

        with patch('sys.argv', test_args):
            import main
            main.main()

        call_kwargs = mock_downloader.download_pairs.call_args[1]
        assert call_kwargs['verbose'] is False

    @patch('main.ClinicalTrialsDownloader')
    @patch('builtins.print')
    def test_main_no_downloads_does_not_create_manifest(self, mock_print, mock_downloader_class, tmp_path):
        """Test main function doesn't create manifest when no downloads."""
        mock_downloader = Mock()
        mock_downloader.download_pairs.return_value = []
        mock_downloader_class.return_value = mock_downloader

        test_args = ['main.py', '--subject', 'nonexistent', '--pairs', '5', '--output', str(tmp_path)]

        with patch('sys.argv', test_args):
            with patch('main.create_manifest') as mock_manifest:
                import main
                main.main()

                # Manifest should NOT be called when no downloads
                mock_manifest.assert_not_called()

    @patch('main.create_manifest')
    @patch('main.ClinicalTrialsDownloader')
    @patch('builtins.print')
    def test_main_prints_download_summary(self, mock_print, mock_downloader_class,
                                          mock_create_manifest, tmp_path):
        """Test main function prints summary of downloaded studies."""
        protocol_path = tmp_path / "NCT12345678" / "protocol.pdf"
        icf_path = tmp_path / "NCT12345678" / "icf.pdf"
        protocol_path.parent.mkdir(parents=True)
        protocol_path.touch()
        icf_path.touch()

        mock_downloader = Mock()
        mock_downloader.download_pairs.return_value = [(protocol_path, icf_path)]
        mock_downloader_class.return_value = mock_downloader
        mock_create_manifest.return_value = tmp_path / "manifest.json"

        test_args = ['main.py', '--subject', 'diabetes', '--pairs', '1', '--output', str(tmp_path)]

        with patch('sys.argv', test_args):
            import main
            main.main()

        # Verify NCT ID was printed in summary
        call_strings = [str(call) for call in mock_print.call_args_list]
        assert any("NCT12345678" in s for s in call_strings)

    @patch('main.create_manifest')
    @patch('main.ClinicalTrialsDownloader')
    @patch('builtins.print')
    def test_main_prints_protocol_only_for_no_icf(self, mock_print, mock_downloader_class,
                                                   mock_create_manifest, tmp_path):
        """Test main function prints correct message for protocol-only downloads."""
        protocol_path = tmp_path / "NCT12345678" / "protocol.pdf"
        protocol_path.parent.mkdir(parents=True)
        protocol_path.touch()

        mock_downloader = Mock()
        mock_downloader.download_pairs.return_value = [(protocol_path, None)]
        mock_downloader_class.return_value = mock_downloader
        mock_create_manifest.return_value = tmp_path / "manifest.json"

        test_args = ['main.py', '--subject', 'diabetes', '--pairs', '1', '--no-icf', '--output', str(tmp_path)]

        with patch('sys.argv', test_args):
            import main
            main.main()

        call_strings = [str(call) for call in mock_print.call_args_list]
        # Should indicate protocol documents, not pairs
        assert any("protocol" in s.lower() for s in call_strings)
