# ClinicalTrials.gov Document Downloader

A Python CLI tool that downloads paired Protocol and Informed Consent Form (ICF) documents from [ClinicalTrials.gov](https://clinicaltrials.gov) using the V2 API.

## Features

- **Search by condition/disease**: Find clinical trials related to specific medical conditions (e.g., "diabetes", "breast cancer")
- **Search by investigator**: Filter trials by principal investigator, co-investigator, or site investigator name
- **Paired document downloads**: Download both Protocol and ICF documents together, or protocols only
- **Automatic rate limiting**: Respects ClinicalTrials.gov API rate limits (~50 requests/minute)
- **Organized output**: Documents are organized by search criteria and NCT ID
- **Manifest generation**: Creates a JSON manifest file documenting all downloaded documents

## Installation

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install requests
```

## Usage

### Basic Examples

```bash
# Download 5 document pairs for diabetes studies
uv run python main.py --subject "diabetes" --pairs 5

# Download 10 pairs for breast cancer studies to a custom directory
uv run python main.py --subject "breast cancer" --pairs 10 --output ./downloads

# Search by investigator name
uv run python main.py --investigator "Frank Moler" --pairs 10

# Combine subject and investigator filters
uv run python main.py --subject "cardiac arrest" --investigator "Frank Moler" --pairs 20

# Download protocols only (without requiring ICF documents)
uv run python main.py --subject "pediatric brain injury" --pairs 50 --no-icf

# Quiet mode (suppress progress output)
uv run python main.py --subject "alzheimer's disease" --pairs 20 --quiet
```

### Command-Line Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--subject` | `-s` | Medical condition/disease to search for | None |
| `--investigator` | `-i` | Investigator name to filter by | None |
| `--pairs` | `-n` | Number of document pairs to download | 5 |
| `--output` | `-o` | Output directory for downloads | `./clinical_trial_documents` |
| `--quiet` | `-q` | Suppress progress output | False |
| `--no-icf` | | Download protocols even without ICF documents | False |

**Note:** At least one of `--subject` or `--investigator` must be provided.

## Output Structure

Documents are organized in the following structure:

```
clinical_trial_documents/
├── diabetes/                          # Search term directory
│   ├── NCT12345678/                   # Study directory (by NCT ID)
│   │   ├── protocol_Protocol_001.pdf
│   │   └── icf_ICF_001.pdf
│   ├── NCT87654321/
│   │   ├── protocol_Protocol_002.pdf
│   │   └── icf_ICF_002.pdf
│   └── ...
└── manifest.json                      # Download manifest
```

When searching by investigator only:
```
clinical_trial_documents/
└── investigator_john_smith/
    └── ...
```

When combining subject and investigator:
```
clinical_trial_documents/
└── diabetes_investigator_john_smith/
    └── ...
```

### Manifest File

A `manifest.json` file is created with metadata about the downloads:

```json
{
  "download_date": "2026-01-19 12:00:00",
  "subject": "diabetes",
  "total_pairs": 5,
  "pairs": [
    {
      "nct_id": "NCT12345678",
      "protocol": "diabetes/NCT12345678/protocol_Protocol_001.pdf",
      "icf": "diabetes/NCT12345678/icf_ICF_001.pdf",
      "clinicaltrials_url": "https://clinicaltrials.gov/study/NCT12345678"
    }
  ]
}
```

## Testing

The project includes a comprehensive test suite with 96% code coverage.

```bash
# Run all tests
uv run pytest

# Run tests with verbose output
uv run pytest -v

# Run tests with coverage report
uv run pytest --cov=main --cov-report=term-missing

# Generate HTML coverage report
uv run pytest --cov=main --cov-report=html
open htmlcov/index.html
```

### Test Structure

- `tests/test_dataclasses.py` - Tests for DocumentInfo and StudyDocuments classes
- `tests/test_downloader.py` - Tests for ClinicalTrialsDownloader class
- `tests/test_manifest.py` - Tests for manifest creation
- `tests/test_cli.py` - Tests for CLI argument parsing and main function
- `tests/test_integration.py` - End-to-end integration tests

## API Information

This tool uses the [ClinicalTrials.gov V2 API](https://clinicaltrials.gov/data-api/api). Key endpoints:

- **Studies endpoint**: `https://clinicaltrials.gov/api/v2/studies`
- **Document URLs**: `https://clinicaltrials.gov/ProvidedDocs/{XX}/{NCTID}/{filename}`

The API allows approximately 50 requests per minute. The tool includes a 1.5-second delay between requests to respect rate limits.

## License

MIT License

## Contributing

Contributions are welcome! Please ensure all tests pass and maintain the existing code coverage level.

```bash
# Before submitting a PR
uv run pytest --cov=main --cov-report=term-missing
```
