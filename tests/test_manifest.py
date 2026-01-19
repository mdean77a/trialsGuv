"""Tests for manifest creation."""
import json
from pathlib import Path
import pytest
from main import create_manifest


class TestCreateManifest:
    """Tests for create_manifest function."""
    
    def test_create_manifest_with_subject(self, temp_output_dir):
        """Test creating manifest with subject."""
        protocol_path = temp_output_dir / "study1" / "protocol.pdf"
        icf_path = temp_output_dir / "study1" / "icf.pdf"
        protocol_path.parent.mkdir()
        protocol_path.touch()
        icf_path.touch()
        
        pairs = [(protocol_path, icf_path)]
        
        manifest_path = create_manifest(
            temp_output_dir,
            subject="diabetes",
            investigator=None,
            pairs=pairs
        )
        
        assert manifest_path.exists()
        
        with open(manifest_path) as f:
            data = json.load(f)
        
        assert data["subject"] == "diabetes"
        assert "investigator" not in data
        assert data["total_pairs"] == 1
        assert len(data["pairs"]) == 1
        assert data["pairs"][0]["nct_id"] == "study1"
    
    def test_create_manifest_with_investigator(self, temp_output_dir):
        """Test creating manifest with investigator."""
        protocol_path = temp_output_dir / "study1" / "protocol.pdf"
        icf_path = temp_output_dir / "study1" / "icf.pdf"
        protocol_path.parent.mkdir()
        protocol_path.touch()
        icf_path.touch()
        
        pairs = [(protocol_path, icf_path)]
        
        manifest_path = create_manifest(
            temp_output_dir,
            subject=None,
            investigator="John Smith",
            pairs=pairs
        )
        
        with open(manifest_path) as f:
            data = json.load(f)
        
        assert "subject" not in data
        assert data["investigator"] == "John Smith"
    
    def test_create_manifest_with_both(self, temp_output_dir):
        """Test creating manifest with both subject and investigator."""
        protocol_path = temp_output_dir / "study1" / "protocol.pdf"
        icf_path = temp_output_dir / "study1" / "icf.pdf"
        protocol_path.parent.mkdir()
        protocol_path.touch()
        icf_path.touch()
        
        pairs = [(protocol_path, icf_path)]
        
        manifest_path = create_manifest(
            temp_output_dir,
            subject="diabetes",
            investigator="John Smith",
            pairs=pairs
        )
        
        with open(manifest_path) as f:
            data = json.load(f)
        
        assert data["subject"] == "diabetes"
        assert data["investigator"] == "John Smith"
    
    def test_create_manifest_without_icf(self, temp_output_dir):
        """Test creating manifest for protocol-only downloads."""
        protocol_path = temp_output_dir / "study1" / "protocol.pdf"
        protocol_path.parent.mkdir()
        protocol_path.touch()
        
        pairs = [(protocol_path, None)]
        
        manifest_path = create_manifest(
            temp_output_dir,
            subject="diabetes",
            investigator=None,
            pairs=pairs
        )
        
        with open(manifest_path) as f:
            data = json.load(f)
        
        assert len(data["pairs"]) == 1
        assert "protocol" in data["pairs"][0]
        assert "icf" not in data["pairs"][0]
    
    def test_create_manifest_multiple_pairs(self, temp_output_dir):
        """Test creating manifest with multiple pairs."""
        pairs = []
        for i in range(3):
            study_dir = temp_output_dir / f"study{i}"
            study_dir.mkdir()
            protocol = study_dir / "protocol.pdf"
            icf = study_dir / "icf.pdf"
            protocol.touch()
            icf.touch()
            pairs.append((protocol, icf))
        
        manifest_path = create_manifest(
            temp_output_dir,
            subject="diabetes",
            investigator=None,
            pairs=pairs
        )
        
        with open(manifest_path) as f:
            data = json.load(f)
        
        assert data["total_pairs"] == 3
        assert len(data["pairs"]) == 3
        assert all("clinicaltrials_url" in pair for pair in data["pairs"])
    
    def test_manifest_has_required_fields(self, temp_output_dir):
        """Test that manifest has all required fields."""
        protocol_path = temp_output_dir / "NCT12345678" / "protocol.pdf"
        icf_path = temp_output_dir / "NCT12345678" / "icf.pdf"
        protocol_path.parent.mkdir()
        protocol_path.touch()
        icf_path.touch()
        
        pairs = [(protocol_path, icf_path)]
        
        manifest_path = create_manifest(
            temp_output_dir,
            subject="diabetes",
            investigator=None,
            pairs=pairs
        )
        
        with open(manifest_path) as f:
            data = json.load(f)
        
        # Check top-level fields
        assert "download_date" in data
        assert "total_pairs" in data
        assert "pairs" in data
        
        # Check pair fields
        pair = data["pairs"][0]
        assert "nct_id" in pair
        assert "protocol" in pair
        assert "icf" in pair
        assert "clinicaltrials_url" in pair
        assert pair["clinicaltrials_url"] == "https://clinicaltrials.gov/study/NCT12345678"
