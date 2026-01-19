"""Tests for dataclass models."""
import pytest
from main import DocumentInfo, StudyDocuments


class TestDocumentInfo:
    """Tests for DocumentInfo dataclass."""
    
    def test_create_document_info(self):
        """Test creating a DocumentInfo instance."""
        doc = DocumentInfo(
            filename="test.pdf",
            size=1024,
            url="https://example.com/test.pdf",
            doc_type="Prot"
        )
        
        assert doc.filename == "test.pdf"
        assert doc.size == 1024
        assert doc.url == "https://example.com/test.pdf"
        assert doc.doc_type == "Prot"
    
    def test_document_info_with_none_size(self):
        """Test DocumentInfo with None size."""
        doc = DocumentInfo(
            filename="test.pdf",
            size=None,
            url="https://example.com/test.pdf",
            doc_type="ICF"
        )
        
        assert doc.size is None


class TestStudyDocuments:
    """Tests for StudyDocuments dataclass."""
    
    def test_has_both_returns_true(self):
        """Test has_both returns True when both documents present."""
        protocol = DocumentInfo("p.pdf", 1024, "url1", "Prot")
        icf = DocumentInfo("i.pdf", 512, "url2", "ICF")
        
        study = StudyDocuments(
            nct_id="NCT12345678",
            brief_title="Test Study",
            protocol=protocol,
            icf=icf
        )
        
        assert study.has_both() is True
    
    def test_has_both_returns_false_no_protocol(self):
        """Test has_both returns False when protocol is missing."""
        icf = DocumentInfo("i.pdf", 512, "url2", "ICF")
        
        study = StudyDocuments(
            nct_id="NCT12345678",
            brief_title="Test Study",
            protocol=None,
            icf=icf
        )
        
        assert study.has_both() is False
    
    def test_has_both_returns_false_no_icf(self):
        """Test has_both returns False when ICF is missing."""
        protocol = DocumentInfo("p.pdf", 1024, "url1", "Prot")
        
        study = StudyDocuments(
            nct_id="NCT12345678",
            brief_title="Test Study",
            protocol=protocol,
            icf=None
        )
        
        assert study.has_both() is False
    
    def test_has_both_returns_false_no_documents(self):
        """Test has_both returns False when no documents present."""
        study = StudyDocuments(
            nct_id="NCT12345678",
            brief_title="Test Study",
            protocol=None,
            icf=None
        )
        
        assert study.has_both() is False
    
    def test_has_protocol_returns_true(self):
        """Test has_protocol returns True when protocol present."""
        protocol = DocumentInfo("p.pdf", 1024, "url1", "Prot")
        
        study = StudyDocuments(
            nct_id="NCT12345678",
            brief_title="Test Study",
            protocol=protocol,
            icf=None
        )
        
        assert study.has_protocol() is True
    
    def test_has_protocol_returns_false(self):
        """Test has_protocol returns False when protocol missing."""
        study = StudyDocuments(
            nct_id="NCT12345678",
            brief_title="Test Study",
            protocol=None,
            icf=None
        )
        
        assert study.has_protocol() is False
