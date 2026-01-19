#!/usr/bin/env python3
"""
ClinicalTrials.gov Document Pair Downloader

Downloads paired Protocol and Informed Consent Form (ICF) documents from 
ClinicalTrials.gov using the V2 API.

Usage:
    python clinicaltrials_document_downloader.py --subject "diabetes" --pairs 5
    python clinicaltrials_document_downloader.py --subject "breast cancer" --pairs 10 --output ./downloads

Requirements:
    pip install requests

Author: Claude (Anthropic)
Date: January 2026
"""

import argparse
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests


# API Configuration
BASE_URL = "https://clinicaltrials.gov/api/v2"
STUDIES_ENDPOINT = f"{BASE_URL}/studies"

# Rate limiting - ClinicalTrials.gov allows ~50 requests/minute
REQUEST_DELAY = 1.5  # seconds between requests


@dataclass
class DocumentInfo:
    """Information about a downloadable document."""
    filename: str
    size: Optional[int]
    url: str
    doc_type: str


@dataclass
class StudyDocuments:
    """Container for a study's paired documents."""
    nct_id: str
    brief_title: str
    protocol: Optional[DocumentInfo]
    icf: Optional[DocumentInfo]
    
    def has_both(self) -> bool:
        """Check if study has both protocol and ICF documents."""
        return self.protocol is not None and self.icf is not None
    
    def has_protocol(self) -> bool:
        """Check if study has protocol document."""
        return self.protocol is not None


@dataclass
class SearchStats:
    """Statistics from a search operation."""
    total_retrieved: int
    with_documents: int
    matching_requirements: int


class ClinicalTrialsDownloader:
    """Downloads clinical trial document pairs from ClinicalTrials.gov."""

    def __init__(self, output_dir: str = "./clinical_trial_documents"):
        self.output_dir = Path(output_dir)
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "ClinicalTrialsDocDownloader/1.0 (Research Tool)"
        })
        self.last_search_stats: Optional[SearchStats] = None
        
    def search_studies_with_documents(
        self,
        subject: str = None,
        investigator: str = None,
        max_results: int = 100,
        page_size: int = 20,
        require_icf: bool = True,
        verbose: bool = True
    ) -> list[dict]:
        """
        Search for studies with protocol documents (and optionally ICF documents).
        
        Args:
            subject: Search term for condition/disease (optional if investigator provided)
            investigator: Investigator name to search for (PI, co-investigator, or site investigator)
            max_results: Maximum number of studies to retrieve
            page_size: Number of results per API call
            require_icf: If True, only return studies with both Protocol and ICF.
                        If False, return studies with at least a Protocol.
            
        Returns:
            List of study data dictionaries matching the document requirements
        """
        all_studies = []
        next_page_token = None
        data = {}  # Initialize data to avoid UnboundLocalError
        
        # Fields we need for document information
        fields = [
            "NCTId",
            "BriefTitle",
            "DocumentSection"
        ]
        
        # Search for more studies than needed since we'll filter for those with both docs
        # Many studies don't have documents, so we need to search broadly
        search_limit = max_results * 50  # Get many extra to account for filtering
        
        while len(all_studies) < search_limit:
            params = {
                "pageSize": min(page_size, search_limit - len(all_studies)),
                "fields": "|".join(fields),
                "countTotal": "true"
            }
            
            # Add condition search if provided
            if subject:
                params["query.cond"] = subject
            
            # Add investigator search if provided
            # This searches ResponsibleParty, OverallOfficial, and Contact fields
            if investigator:
                params["query.term"] = investigator
            
            if next_page_token:
                params["pageToken"] = next_page_token
                
            try:
                if verbose:
                    print(f"  Searching... (retrieved {len(all_studies)} so far)")
                response = self.session.get(STUDIES_ENDPOINT, params=params)
                response.raise_for_status()
                data = response.json()
                
                # Extract studies from response
                study_list = data.get("studies", [])
                if not study_list:
                    if verbose:
                        print(f"  No more studies found.")
                    break
                    
                all_studies.extend(study_list)
                
                # Check for next page
                next_page_token = data.get("nextPageToken")
                if not next_page_token:
                    break
                    
                # Respect rate limits
                time.sleep(REQUEST_DELAY)
                
            except requests.exceptions.RequestException as e:
                if verbose:
                    print(f"  Error searching studies: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    if e.response.status_code == 429:
                        if verbose:
                            print("  Rate limited. Waiting 60 seconds...")
                        time.sleep(60)
                        continue
                break
        
        # Filter studies based on document requirements
        filtered_studies = []
        studies_with_docs = 0
        for study in all_studies:
            # Check if study has document section
            if study.get("documentSection"):
                studies_with_docs += 1
            study_docs = self.extract_document_info(study, debug=False)
            
            # Check if study meets document requirements
            if require_icf:
                if study_docs.has_both():
                    filtered_studies.append(study)
            else:
                if study_docs.has_protocol():
                    filtered_studies.append(study)
            
            if len(filtered_studies) >= max_results:
                break

        # Store statistics for later use
        self.last_search_stats = SearchStats(
            total_retrieved=len(all_studies),
            with_documents=studies_with_docs,
            matching_requirements=len(filtered_studies)
        )

        if verbose:
            print(f"  Retrieved {len(all_studies)} studies total")
            print(f"  {studies_with_docs} studies have document sections")
            if require_icf:
                print(f"  Found {len(filtered_studies)} studies with both Protocol and ICF documents")
            else:
                print(f"  Found {len(filtered_studies)} studies with Protocol documents")
        return filtered_studies
    
    def extract_document_info(self, study: dict, debug: bool = False) -> StudyDocuments:
        """
        Extract protocol and ICF document info from a study.
        
        Args:
            study: Study data dictionary from API
            debug: Print debug information
            
        Returns:
            StudyDocuments object with document information
        """
        protocol_section = study.get("protocolSection", {})
        ident_module = protocol_section.get("identificationModule", {})
        
        nct_id = ident_module.get("nctId", "Unknown")
        brief_title = ident_module.get("briefTitle", "Unknown")
        
        # Navigate to document section
        doc_section = study.get("documentSection", {})
        large_docs = doc_section.get("largeDocumentModule", {})
        large_docs_list = large_docs.get("largeDocs", [])
        
        if debug and large_docs_list:
            print(f"\n  DEBUG {nct_id}: {len(large_docs_list)} documents found")
        
        protocol = None
        icf = None
        
        for doc in large_docs_list:
            type_abbrev = doc.get("typeAbbrev", "")
            has_protocol = doc.get("hasProtocol", False)
            has_icf = doc.get("hasIcf", False)
            
            if debug:
                print(f"    - {type_abbrev}: hasProtocol={has_protocol}, hasIcf={has_icf}")
            
            filename = doc.get("filename", "")
            size = doc.get("size")
            
            # Construct download URL
            # Format: https://clinicaltrials.gov/ProvidedDocs/{XX}/{NCTID}/{filename}
            # Where XX is the last 2 digits of NCT number
            nct_suffix = nct_id[-2:] if len(nct_id) >= 2 else "00"
            doc_url = f"https://clinicaltrials.gov/ProvidedDocs/{nct_suffix}/{nct_id}/{filename}"
            
            doc_info = DocumentInfo(
                filename=filename,
                size=size,
                url=doc_url,
                doc_type=type_abbrev
            )
            
            # Check if this document contains protocol
            if has_protocol and protocol is None:
                protocol = doc_info
                
            # Check if this document contains ICF
            if has_icf and icf is None:
                icf = doc_info
                
        return StudyDocuments(
            nct_id=nct_id,
            brief_title=brief_title,
            protocol=protocol,
            icf=icf
        )
    
    def download_document(self, doc: DocumentInfo, save_path: Path) -> bool:
        """
        Download a document and save to disk.
        
        Args:
            doc: DocumentInfo object with URL and filename
            save_path: Path where file should be saved
            
        Returns:
            True if download successful, False otherwise
        """
        try:
            response = self.session.get(doc.url, stream=True)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"    Error downloading {doc.filename}: {e}")
            return False
    
    def download_pairs(
        self, 
        subject: str = None,
        investigator: str = None,
        num_pairs: int = 5,
        verbose: bool = True,
        require_icf: bool = True
    ) -> list[tuple[Path, Optional[Path]]]:
        """
        Download protocol documents (and optionally ICF documents).
        
        Args:
            subject: Search term for condition/disease (optional if investigator provided)
            investigator: Investigator name to filter by (optional)
            num_pairs: Number of document pairs to download
            verbose: Print progress information
            require_icf: If True, require both Protocol and ICF documents.
                        If False, download Protocol even without ICF.
            
        Returns:
            List of tuples containing (protocol_path, icf_path) for successful downloads.
            If require_icf=False, icf_path may be None.
        """
        # Create output directory structure
        # Build directory name based on search criteria
        dir_parts = []
        if subject:
            dir_parts.append(self._sanitize_filename(subject))
        if investigator:
            dir_parts.append(f"investigator_{self._sanitize_filename(investigator)}")
        
        if not dir_parts:
            dir_parts.append("all_studies")
        
        subject_dir = self.output_dir / "_".join(dir_parts)
        subject_dir.mkdir(parents=True, exist_ok=True)
        
        # Build search description
        search_desc = []
        if subject:
            search_desc.append(f"about '{subject}'")
        if investigator:
            search_desc.append(f"by investigator '{investigator}'")
        if not search_desc:
            search_desc.append("for all studies")
        
        if verbose:
            if require_icf:
                print(f"\nSearching for studies {' and '.join(search_desc)} with both Protocol and ICF documents...")
            else:
                print(f"\nSearching for studies {' and '.join(search_desc)} with Protocol documents...")
        
        # Search for studies - get extra in case some downloads fail
        search_multiplier = 2
        studies = self.search_studies_with_documents(
            subject=subject,
            investigator=investigator,
            max_results=num_pairs * search_multiplier,
            require_icf=require_icf,
            verbose=verbose
        )
        
        if not studies:
            if verbose:
                if require_icf:
                    print("No studies found with both document types.")
                else:
                    print("No studies found with protocol documents.")
            return []
        
        downloaded_pairs = []

        for study in studies:
            if len(downloaded_pairs) >= num_pairs:
                break

            study_docs = self.extract_document_info(study)

            if verbose:
                print(f"\n[{len(downloaded_pairs) + 1}/{num_pairs}] {study_docs.nct_id}: {study_docs.brief_title[:60]}...")
            
            # Create study-specific directory
            study_dir = subject_dir / study_docs.nct_id
            study_dir.mkdir(exist_ok=True)
            
            # Download protocol
            protocol_path = study_dir / f"protocol_{study_docs.protocol.filename}"
            if verbose:
                print(f"  Downloading Protocol: {study_docs.protocol.filename}")
            protocol_success = self.download_document(study_docs.protocol, protocol_path)
            time.sleep(REQUEST_DELAY)
            
            # Download ICF if present
            icf_path = None
            icf_success = True  # Default to True if ICF not required
            if study_docs.icf:
                icf_path = study_dir / f"icf_{study_docs.icf.filename}"
                if verbose:
                    print(f"  Downloading ICF: {study_docs.icf.filename}")
                icf_success = self.download_document(study_docs.icf, icf_path)
                time.sleep(REQUEST_DELAY)
            elif verbose and require_icf:
                print(f"  Note: No ICF document available")
            
            # Determine success based on requirements
            if require_icf:
                success = protocol_success and icf_success
            else:
                success = protocol_success
            
            if success:
                downloaded_pairs.append((protocol_path, icf_path))
                if verbose:
                    if icf_path:
                        print(f"  ✓ Successfully downloaded pair")
                    else:
                        print(f"  ✓ Successfully downloaded protocol")
            else:
                # Clean up partial downloads
                if protocol_path.exists():
                    protocol_path.unlink()
                if icf_path and icf_path.exists():
                    icf_path.unlink()
                if study_dir.exists() and not any(study_dir.iterdir()):
                    study_dir.rmdir()
                if verbose:
                    print(f"  ✗ Failed to download")
        
        return downloaded_pairs
    
    def _sanitize_filename(self, name: str) -> str:
        """Convert a string to a safe filename."""
        # Replace spaces and special characters
        safe_name = re.sub(r'[^\w\s-]', '', name)
        safe_name = re.sub(r'[-\s]+', '_', safe_name)
        return safe_name.strip('_').lower()


def main():
    parser = argparse.ArgumentParser(
        description="Download paired Protocol and ICF documents from ClinicalTrials.gov",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --subject "diabetes" --pairs 5
  %(prog)s --subject "breast cancer" --pairs 10 --output ./downloads
  %(prog)s --subject "alzheimer's disease" --pairs 20 --quiet
  %(prog)s --subject "pediatric brain injury" --pairs 50 --no-icf
  %(prog)s --investigator "Frank Moler" --pairs 10
  %(prog)s --subject "cardiac arrest" --investigator "Frank Moler" --pairs 20
        """
    )
    
    parser.add_argument(
        "--subject", "-s",
        help="Medical condition/disease to search for"
    )
    
    parser.add_argument(
        "--investigator", "-i",
        help="Investigator name to filter by (PI, co-investigator, or site investigator)"
    )
    
    parser.add_argument(
        "--pairs", "-n",
        type=int,
        default=5,
        help="Number of document pairs to download (default: 5)"
    )
    
    parser.add_argument(
        "--output", "-o",
        default="./clinical_trial_documents",
        help="Output directory (default: ./clinical_trial_documents)"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress progress output"
    )
    
    parser.add_argument(
        "--no-icf",
        action="store_true",
        help="Download protocols even without ICF documents (default: require both)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.subject and not args.investigator:
        print("Error: Must provide at least one of --subject or --investigator")
        sys.exit(1)
    
    if args.pairs < 1:
        print("Error: Number of pairs must be at least 1")
        sys.exit(1)
    
    # Create downloader and run
    downloader = ClinicalTrialsDownloader(output_dir=args.output)
    
    print(f"=" * 60)
    print(f"ClinicalTrials.gov Document Pair Downloader")
    print(f"=" * 60)
    if args.subject:
        print(f"Subject: {args.subject}")
    if args.investigator:
        print(f"Investigator: {args.investigator}")
    print(f"Pairs requested: {args.pairs}")
    print(f"Output directory: {args.output}")
    
    downloaded_pairs = downloader.download_pairs(
        subject=args.subject,
        investigator=args.investigator,
        num_pairs=args.pairs,
        verbose=not args.quiet,
        require_icf=not args.no_icf
    )
    
    print(f"\n{'=' * 60}")
    print(f"Summary")
    print(f"{'=' * 60}")

    # Display search statistics
    if downloader.last_search_stats:
        stats = downloader.last_search_stats
        print(f"Studies retrieved from API: {stats.total_retrieved}")
        print(f"Studies with document sections: {stats.with_documents}")
        if args.no_icf:
            print(f"Studies with Protocol documents: {stats.matching_requirements}")
        else:
            print(f"Studies with Protocol + ICF: {stats.matching_requirements}")

    if downloaded_pairs:
        if args.no_icf:
            print(f"Successfully downloaded: {len(downloaded_pairs)} protocol documents")
        else:
            print(f"Successfully downloaded: {len(downloaded_pairs)} document pairs")
        print(f"\nDocuments saved to: {args.output}/")

        print(f"\nDownloaded studies:")
        for protocol_path, icf_path in downloaded_pairs:
            nct_id = protocol_path.parent.name
            if icf_path:
                print(f"  - {nct_id} (Protocol + ICF)")
            else:
                print(f"  - {nct_id} (Protocol only)")
    else:
        print(f"Successfully downloaded: 0")
        print("\nNo documents were downloaded. This could be due to:")
        print("  - No studies found matching the search criteria")
        print("  - Network issues during download")
        print("  - Rate limiting by the API")
        print("Try a different search term or try again later.")


if __name__ == "__main__":
    main()