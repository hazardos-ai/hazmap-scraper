# HazMap Scraper - Technical Specifications

## Architecture Overview

### System Components
```
hazmap-scraper/
├── src/
│   ├── models/           # Data models and validation
│   ├── scripts/          # Core scraping engines
│   └── hazmap_scraper/   # Main package
├── data/
│   ├── raw_html/         # Downloaded HTML files
│   ├── formatted/        # Processed output files
│   └── registry/         # YAML entity registries
├── tests/                # Test suite
└── run_scraper.py        # Advanced CLI interface
```

## Core Technologies

### Runtime Environment
- **Python**: >= 3.11 (required for modern type hints and performance)
- **Package Manager**: Pixi (conda-forge based dependency management)
- **Containerization**: GitHub Codespaces with ghcr.io/hazardos-ai/base:latest

### Dependencies
```toml
requests = ">=2.32.4,<3"      # HTTP client for web scraping
pydantic = ">=2.11.7,<3"      # Data validation and serialization
pyyaml = ">=6.0.2,<7"         # YAML configuration parsing
beautifulsoup4 = ">=4.12.2,<5" # HTML parsing and extraction
pytest = ">=8.4.1,<9"         # Testing framework
```

## Data Models

### EntityEntry (Pydantic v2)
```python
class EntityEntry(BaseModel):
    name: str                    # Entity name extracted from HTML
    url: HttpUrl                 # Source URL (validated)
    uuid: str                    # Generated UUID4 identifier
    # Note: 'category' field removed for cleaner data structure
```

### CategoryRegistry
```python
class CategoryRegistry(BaseModel):
    category: str                # Category name (agents, diseases, etc.)
    entities: List[EntityEntry]  # List of scraped entities
    total_scraped: int          # Count of successfully scraped entities
    timestamp: str              # ISO format timestamp
```

### EntityRegistry
```python
class EntityRegistry(BaseModel):
    categories: Dict[str, CategoryRegistry]  # All categories
    metadata: Dict[str, Any]                # Additional metadata
```

### Knowledge Graph Schema
The system supports comprehensive graph database integration with:

#### Node Types (8 categories):
- **Agent**: Hazardous substances with CAS numbers, formulas, regulatory classifications
- **Disease**: Occupational diseases with clinical metadata
- **Process**: Industrial processes with risk profiles
- **Industry**: Industry classifications with NAICS codes
- **JobTask**: Specific workplace tasks with exposure risks
- **Job**: Occupational roles with SOC codes
- **Finding**: Medical symptoms and findings
- **Activity**: Non-occupational exposure activities

#### Relationship Types (9 types):
- **CAUSES**: Agent → Disease (causal relationships)
- **MANIFESTS_AS**: Disease → Finding (symptom manifestation)
- **EXPOSED_TO**: Job/JobTask → Agent (exposure risks)
- **INVOLVES_TASK**: Job → JobTask (task associations)
- **OPERATES_IN**: Job → Industry (industry context)
- **INVOLVES_PROCESS**: Industry → Process (process usage)
- **USES_AGENT**: Process → Agent (agent usage)
- **INVOLVES_ACTIVITY**: Activity → Agent (activity exposure)
- **SIMILAR_TO**: Entity → Entity (similarity relationships)

#### Cross-Reference Metadata:
- Confidence scoring (0.0-1.0)
- Reference type (name_match, url_match)
- Source text attribution
- UUID-based entity linking

## Scraping Engine Specifications

### HazMapScraper Class
```python
class HazMapScraper:
    def __init__(
        self,
        sitemap_path: str = "src/models/sitemap.yml",
        delay: Optional[float] = None  # No rate limiting by default
    )
```

#### Key Methods
- `extract_entity_name()`: Multi-strategy content extraction
- `is_valid_entity_name()`: Content validation and filtering
- `scrape_entity()`: Single entity processing
- `scrape_category()`: Category-level processing
- `scrape_all()`: Full site processing

#### Content Extraction Strategy
1. **Primary selectors**: `h1`, `title`
2. **Secondary selectors**: `.page-title`, `#title`, `h2`
3. **Fallback selectors**: `.entity-name`, meta tags
4. **Validation**: Apply filtering rules to extracted content

#### Filtering Rules
```python
invalid_names = [
    "| Haz-Map", "| HazMap", "Haz-Map", "HazMap",
    "Server Error Occured", "Server Error Occurred",
    "page not found", "error", "404"
]
```

## Advanced CLI Processor

### HazMapProcessor Class
```python
class HazMapProcessor:
    def __init__(self, delay: Optional[float] = None)
```

#### Processing Modes
- **HTML Mode**: Process existing files from `data/raw_html/`
- **Registry Mode**: Fresh scraping based on YAML registries
- **Single File Mode**: Process individual HTML files
- **Category Mode**: Process specific entity categories

#### Output Formats
- **Clean**: Human-readable structured text
- **Structured**: Field-organized output for analysis
- **JSON**: Machine-readable format for APIs

## File Organization Specifications

### Directory Structure
```
data/
├── raw_html/                    # Complete HTML backup
│   ├── agents/                  # Category subdirectories
│   │   └── {uuid}_{name}.html   # UUID-prefixed filenames
│   ├── diseases/
│   └── [other categories]/
├── formatted/                   # Processed output
│   ├── clean/                   # Human-readable text
│   ├── structured/              # Organized field data
│   └── json/                    # Machine-readable JSON
└── registry/                    # Entity registries
    └── {category}_registry_{timestamp}.yml
```

### File Naming Conventions
- **Registry files**: `{category}_registry_YYYYMMDD_HHMMSS.yml`
- **HTML files**: `{uuid}_{safe_name}.html` (UUID + sanitized name)
- **Output files**: `{uuid}_{safe_name}.{extension}`

## Configuration System

### Sitemap Configuration
```yaml
# src/models/sitemap.yml
categories:
  agents:
    name: "Hazardous Agents"
    description: "Hazardous Agents"
    root_url: "https://haz-map.com/Agents/"
  diseases:
    name: "Occupational Diseases"
    description: "Occupational Diseases"
    root_url: "https://haz-map.com/Diseases/"
  # ... additional categories
```

## Performance Specifications

### Rate Limiting
- **Default**: No rate limiting (delay=None) for maximum speed
- **Optional**: Configurable delays via `--delay` parameter
- **Respectful**: Professional User-Agent and optional throttling

### Processing Capacity
- **Small tests**: ~10 seconds (3 entities)
- **Disease category**: ~15 minutes (428 entities)
- **Process category**: ~8 minutes (227 entities)
- **Full agents**: ~6-8 hours (21,500+ entities)
- **Complete processing**: ~8-12 hours total

### Storage Requirements
- **Raw HTML**: ~1.2 GB for all categories
- **Formatted output**: ~500 MB for all formats
- **Registry files**: ~50 MB total

## Automation & CI/CD

### GitHub Actions Workflow
```yaml
name: Scrape HazMap Registry
on:
  workflow_dispatch:
  schedule:
    - cron: '0 2 * * 0'  # Weekly on Sundays

jobs:
  scrape:
    runs-on: ubuntu-latest
    timeout-minutes: 60
```

#### Workflow Features
- **Automated scheduling**: Weekly registry updates
- **Manual triggers**: On-demand execution via workflow_dispatch
- **Git conflict resolution**: Robust handling of concurrent updates
- **Retry logic**: Multiple push attempts with conflict resolution
- **Conventional commits**: Automated commit message formatting

### Pixi Task Integration
```bash
# Core scraping tasks
pixi run scrape-registry      # Build entity registries
pixi run scrape-raw-html      # Download HTML files
pixi run scrape-detailed      # Extract structured data

# Advanced CLI tasks  
pixi run process              # Default processing
pixi run process-test         # Limited test processing
pixi run process-agents       # Category-specific processing

# Development tasks
pixi run test                 # Test suite execution
pixi run lint                 # Code syntax checking
pixi run clean                # Cache cleanup
```

## Error Handling & Resilience

### HTTP Error Handling
- **Connection errors**: Automatic retry with exponential backoff
- **HTTP 404/500**: Graceful skipping with logging
- **Timeout handling**: Configurable request timeouts
- **Rate limiting response**: Automatic delay adjustment

### Data Validation
- **Pydantic validation**: Automatic data type and format validation
- **Content filtering**: Multi-layer validation rules
- **UUID uniqueness**: Collision detection and regeneration
- **URL validation**: HttpUrl type ensures valid URLs

### Recovery Mechanisms
- **Resume capability**: Skip already processed files
- **Interrupt handling**: Clean shutdown on KeyboardInterrupt
- **Progress preservation**: Intermediate saves during processing
- **Detailed logging**: Comprehensive error reporting

## Testing Specifications

### Test Coverage
- **Unit tests**: Individual component testing with mocking
- **Integration tests**: End-to-end workflow validation
- **Mocked HTTP**: Controlled testing without network dependency
- **Validation testing**: Data model and filtering rule verification

### Test Categories
```python
class TestHazMapScraper:
    def test_scraper_initialization()      # Configuration loading
    def test_is_valid_entity_name()        # Filtering validation
    def test_scrape_entity_success()       # Successful extraction
    def test_scrape_entity_invalid_name()  # Invalid content handling
    def test_scrape_entity_http_error()    # Error condition handling
```

## Security & Compliance

### Web Scraping Ethics
- **Respectful rate limiting**: Optional delays to avoid server overload
- **Professional User-Agent**: Clear identification of scraping tool
- **Public data only**: Only extracts publicly available information
- **No authentication bypass**: Respects website access controls

### Data Handling
- **No personal data**: Focuses on occupational health information
- **Public domain content**: Medical and safety information
- **Attribution preserved**: Maintains source URLs and metadata
- **Version control**: Git-based tracking of all data changes