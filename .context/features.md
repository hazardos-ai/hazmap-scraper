# HazMap Scraper - Features Documentation

## Core Features

### 🚀 Web Scraping Engine
- **Multi-source scraping**: Extracts data from haz-map.com using configurable sitemap
- **Smart content extraction**: Uses multiple CSS selectors (h1, title, .page-title, #title, h2, .entity-name, meta tags)
- **HTTP error handling**: Graceful handling of 404s, timeouts, and connection errors
- **User-agent simulation**: Professional User-Agent headers to avoid blocking

### 🔍 Intelligent Filtering
- **Invalid entry detection**: Automatically skips entries with placeholder titles like "| Haz-Map"
- **Server error filtering**: Detects and skips pages containing "Server Error Occured" 
- **Content validation**: Validates extracted entity names against known invalid patterns
- **Duplicate prevention**: UUID-based tracking prevents processing the same entity twice

### ⚡ Performance Optimization
- **Optional rate limiting**: Configurable delays between requests (disabled by default for speed)
- **Resume capability**: Skips already processed files to avoid redundant work
- **Progress tracking**: Real-time progress indicators with detailed logging
- **Batch processing**: Efficient processing of multiple categories and entities

### 📊 Multiple Output Formats
- **Clean format**: Human-readable text output with structured fields
- **Structured format**: Organized field-based output for analysis
- **JSON format**: Machine-readable format for APIs and databases
- **Raw HTML preservation**: Complete HTML backup for alternative processing

### 🎯 Flexible Input Sources
- **HTML processing**: Process existing HTML files from `data/raw_html/`
- **Registry-based scraping**: Fresh scraping based on YAML registry files
- **Single file processing**: Process individual HTML files
- **Category-specific processing**: Target specific entity categories

### 🔧 Advanced CLI Interface
- **Argument-based configuration**: Comprehensive command-line options
- **Source selection**: Choose between HTML files or fresh scraping
- **Format selection**: Specify output format (clean, structured, JSON)
- **Limit controls**: Set processing limits for testing and partial runs
- **Category filtering**: Process specific categories or all categories

### 📁 Data Organization
- **Timestamped files**: All registry files include creation timestamps
- **Category-based structure**: Organized by entity types (agents, diseases, jobs, etc.)
- **UUID generation**: Unique identifiers for all entities
- **Metadata preservation**: Entity URLs, names, categories, and timestamps

### 🛡️ Error Handling & Resilience
- **HTTP error recovery**: Graceful handling of network issues
- **Content validation**: Multiple layers of data validation
- **Interrupt handling**: Clean shutdown on user interruption
- **Detailed logging**: Comprehensive error reporting and debugging info

### 🔄 Automation Support
- **GitHub Actions integration**: Automated scraping workflows
- **Pixi task integration**: Pre-configured development tasks
- **CI/CD compatibility**: Suitable for continuous integration pipelines
- **Git conflict resolution**: Robust handling of concurrent updates

## Supported Entity Categories

- **Agents** (~21,500 entities): Hazardous agents and substances
- **Diseases** (~428 entities): Occupational diseases and conditions
- **Processes** (~227 entities): Industrial and manufacturing processes  
- **Activities** (~39 entities): Non-occupational activities
- **Findings** (~248 entities): Symptoms and medical findings
- **Industries** (~307 entities): Industry classifications
- **Job Tasks** (~304 entities): Specific workplace tasks
- **Jobs** (~493 entities): High-risk occupational roles

## Technical Capabilities

### Data Processing Pipeline
1. **Registry Discovery**: Load sitemap configuration and entity URLs
2. **Content Extraction**: Download and parse HTML content
3. **Data Validation**: Apply filtering rules and content validation
4. **Format Conversion**: Convert to requested output format
5. **File Organization**: Save with proper naming and directory structure
6. **Cross-reference Analysis**: Generate entity relationships with confidence scoring

### Knowledge Graph Integration ✅ MIGRATED + VECTOR EMBEDDINGS
- **Graph Schema**: ✅ Comprehensive node and relationship definitions for Neo4j
- **Entity Linking**: ✅ Automated cross-referencing between 12,848 entities **COMPLETED**
- **Relationship Mapping**: ✅ 9 distinct relationship types with metadata **115,828 relationships created**
- **Confidence Scoring**: ✅ Quality metrics for all entity connections (1.0 required for migration)
- **Schema Evolution**: ✅ Versioned schema supporting future enhancements
- **Neo4j Migration**: ✅ Complete pipeline for migrating JSON data to knowledge graph **EXECUTED**
- **Database Connectivity**: ✅ Environment-based configuration for secure connections
- **Migration Testing**: ✅ Comprehensive test suite for data integrity verification
- **Production Database**: ✅ **LIVE - 12,848 nodes across 8 types, 115,828 high-confidence relationships**
- **Data Quality**: ✅ **VERIFIED - 100% UUID coverage, confidence filtering applied**
- **Vector Embeddings**: ✅ **NEW** - OpenAI-powered semantic search with 1536-dimensional embeddings
- **Vector Indices**: ✅ **NEW** - Cosine similarity search across all entity types
- **Semantic Search**: ✅ **NEW** - Cross-category similarity matching for enhanced discovery

### Quality Assurance
- **Content validation**: Multiple validation layers for data quality
- **Error detection**: Automatic identification of problematic entries
- **Resume capability**: Skip already processed files
- **Progress monitoring**: Real-time feedback on processing status
- **Relationship Validation**: Cross-reference integrity checking

### Development Features
- **Test suite**: Comprehensive unit tests with mocking
- **Modular design**: Separate concerns for scraping, processing, and output
- **Configuration management**: YAML-based configuration system
- **Documentation**: Comprehensive inline documentation and examples
- **Graph Schema Documentation**: Complete schema specification for knowledge graph implementation