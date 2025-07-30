# HazMap Scraper Suite

A comprehensive automated scraping system for extracting data from haz-map.com. This project provides multiple scrapers and processing tools to build UUID-based registries and extract structured data for Neo4j knowledge graph construction.

## 🚀 Quick Start

### Using the CLI (Recommended)

The easiest way to get started is with the advanced CLI processor:

```bash
# Install dependencies
pixi install

# Process all HTML files as JSON (default behavior)
python run_scraper.py

# Process with limits for testing
python run_scraper.py --limit 1

# Process specific category
python run_scraper.py --category agents --format structured

# Process single file
python run_scraper.py --file data/raw_html/agents/uuid_filename.html --format clean
```

### Using Pixi Tasks

```bash
# Quick status check
pixi run status

# Test different scrapers
pixi run test-registry
pixi run test-detailed  
pixi run test-raw-html

# Process data with the new CLI
pixi run process-test
pixi run process-agents
pixi run process-clean
```

## 🛠️ Tools Overview

This project includes three main components:

### 1. Registry Scraper (`scrape_registry.py`)
- **Purpose**: Build UUID-based entity registries from category pages
- **Output**: YAML registry files with entity metadata
- **Use Case**: Initial discovery and cataloging of all entities

### 2. Raw HTML Scraper (`raw_html_scraper.py`)
- **Purpose**: Download complete HTML source for backup and future processing
- **Output**: HTML files with metadata headers in `data/raw_html/`
- **Use Case**: Complete data preservation and alternative processing approaches

### 3. Advanced CLI Processor (`run_scraper.py`)
- **Purpose**: Flexible processing of HTML files or fresh scraping from registries
- **Output**: Multiple formats (clean, structured, JSON) in `data/formatted/`
- **Use Case**: Production data processing with flexible input/output options

### 4. Neo4j Migration (`neo4j_migration.py`) ✅ **COMPLETED**
- **Purpose**: Migrate JSON data to Neo4j knowledge graph database
- **Output**: Populated Neo4j database with nodes and relationships  
- **Use Case**: Building a knowledge graph for advanced analytics and querying
- **Status**: ✅ **LIVE DATABASE** - 12,848 nodes and 115,828 relationships migrated
- **Verification**: ✅ All expected data successfully migrated and verified

## 📊 Features

- ✅ **Smart Filtering**: Automatically skips invalid entries like "| Haz-Map"
- ✅ **Multiple Output Formats**: Clean text, structured data, and JSON
- ✅ **Flexible Input Sources**: Process existing HTML or scrape fresh from registries  
- ✅ **Timestamped Files**: Registry files with timestamps for version tracking
- ✅ **Progress Tracking**: Real-time progress during scraping operations
- ✅ **Resume Capability**: Skip already processed files
- ✅ **Rate Limiting**: Configurable delays between requests
- ✅ **UUID Generation**: Unique identifiers for all entities
- ✅ **Comprehensive CLI**: Advanced argument-based interface
- ✅ **Pixi Integration**: Pre-configured tasks for common operations
- ✅ **Neo4j Integration**: Direct migration to knowledge graph database ✅ **COMPLETED**
- ✅ **Graph Schema Compliance**: Follows defined node and relationship structure
- ✅ **Confidence Filtering**: Only migrates relationships with confidence score 1.0
- ✅ **Production Database**: ✅ **LIVE** - 12,848 nodes, 115,828 relationships migrated

## 📁 Data Structure

```
data/
├── registry/                     # Entity registries (YAML)
│   ├── activities_registry_*.yml
│   ├── agents_registry_*.yml
│   └── ...
├── raw_html/                     # Complete HTML files
│   ├── agents/
│   │   ├── {uuid}_{name}.html
│   │   └── ...
│   └── ...
└── formatted/                    # Processed output
    ├── clean/                    # Human-readable text
    ├── structured/               # Organized field data
    └── json/                     # Machine-readable JSON
        ├── agents/
        ├── diseases/
        └── ...
```

## 📋 Registry Files

Registry files contain entity catalogs in YAML format:

```yaml
category: agents
category_name: Hazardous Agents
category_description: Hazardous Agents
root_url: https://haz-map.com/Agents/
total_expected: 21499
total_scraped: 15234
scraped_at: 2025-07-16T12:00:00.000000
entities:
  - uuid: 123e4567-e89b-12d3-a456-426614174000
    name: Asbestos
    url: https://haz-map.com/Agents/1
  - uuid: 456e7890-e89b-12d3-a456-426614174001
    name: Cadmium
    url: https://haz-map.com/Agents/2
```

## 🎯 Available Categories

- **agents** - Hazardous agents (~21,500 entities)
- **diseases** - Occupational diseases (~428 entities)  
- **processes** - Industrial processes (~227 entities)
- **activities** - Non-occupational activities (~39 entities)
- **findings** - Symptoms/findings (~248 entities)
- **industries** - Industries (~307 entities)
- **job_tasks** - Job tasks (~304 entities)
- **jobs** - High risk jobs (~493 entities)

## 💻 CLI Usage Examples

### Basic Processing
```bash
# Default: Process all HTML files as JSON
python run_scraper.py

# Process specific category from existing HTML
python run_scraper.py --source html --category agents --format json

# Fresh scraping from registry
python run_scraper.py --source registry --category diseases --limit 10 --format structured

# Process single file
python run_scraper.py --file data/raw_html/agents/uuid_filename.html --format clean
```

### Output Formats
```bash
# Clean text format (human-readable)
python run_scraper.py --format clean --limit 1

# Structured format (organized fields)
python run_scraper.py --format structured --limit 1

# JSON format (machine-readable)
python run_scraper.py --format json --limit 1
```

### Testing and Development
```bash
# Test with limits
python run_scraper.py --limit 5

# Custom rate limiting for fresh scraping
python run_scraper.py --source registry --delay 2.0 --limit 3

# Process all categories with limits
python run_scraper.py --limit 1
```

## 🔧 Configuration

The scraper uses `src/models/sitemap.yml` to define categories:

```yaml
categories:
  activities:
    name: Activities
    description: Activities
    root_url: https://haz-map.com/Activities/
  agents:
    name: Hazardous Agents  
    description: Hazardous Agents
    root_url: https://haz-map.com/Agents/
  # ... more categories
```

## ⚡ Performance

### Estimated Processing Times
- **Test (3 entities)**: ~10 seconds
- **All diseases**: ~15 minutes  
- **All processes**: ~8 minutes
- **All agents**: ~6-8 hours (21,500+ entities)
- **Full processing**: ~8-12 hours total

### Storage Requirements
- **Raw HTML**: ~1.2 GB for all categories
- **Formatted Output**: ~500 MB for all formats
- **Registry Files**: ~50 MB total

## 💻 Development

### Environment Setup

The project requires specific environment variables for Neo4j connectivity:

```bash
# Required for Neo4j migration
export NEO4J_CONNECTION_URI="bolt://localhost:7687"  # or your Neo4j instance
export NEO4J_USERNAME="neo4j"                        # your Neo4j username
export NEO4J_PASSWORD="your_password"                # your Neo4j password
export NEO4J_QUERY_API_URL="http://localhost:7474"  # optional: for HTTP API access
```

### Available Pixi Tasks
```bash
# Scraping tasks
pixi run scrape-registry         # Build entity registries
pixi run scrape-detailed         # Extract structured data
pixi run scrape-raw-html         # Download HTML files

# Testing tasks  
pixi run test-registry           # Test registry building
pixi run test-detailed           # Test data extraction
pixi run test-raw-html           # Test HTML downloads

# Processing tasks
pixi run process                 # Advanced CLI processor
pixi run process-test            # Process with limits
pixi run process-agents          # Process agents category
pixi run process-from-registry   # Fresh scraping

# Output format tasks
pixi run process-clean           # Clean text output
pixi run process-structured      # Structured field output  
pixi run process-json            # JSON output

# Neo4j migration tasks
pixi run neo4j-test              # Test Neo4j connection
pixi run neo4j-migrate           # Migrate all data to Neo4j
pixi run neo4j-migrate-sample    # Migrate sample data (100 entities)
pixi run neo4j-migrate-with-vectors  # Full migration including vector embeddings

# Vector embedding tasks
pixi run add-vector-embeddings   # Add semantic search to existing graph

# Utility tasks
pixi run test                    # Run test suite
pixi run lint                    # Check code syntax
pixi run clean                   # Remove cache files
pixi run status                  # Show project status
```

### Data Models

The scraper uses Pydantic models for validation:

```python
class EntityEntry(BaseModel):
    uuid: str
    name: str
    url: str

class CategoryRegistry(BaseModel):
    category: str
    category_name: str
    category_description: str
    root_url: str
    total_expected: int
    total_scraped: int
    scraped_at: str
    entities: List[EntityEntry]
```

## 🔄 Workflow Examples

### Complete Data Pipeline
```bash
# 1. Build registries
pixi run scrape-registry

# 2. Download raw HTML (optional)
pixi run scrape-raw-html

# 3. Process to structured formats
python run_scraper.py --format json

# 4. Test Neo4j connection
pixi run neo4j-test

# 5. Migrate to Neo4j database
pixi run neo4j-migrate

# 6. Check status
pixi run status
```

### Neo4j Migration Workflow ✅ **COMPLETED**
```bash
# 1. Set environment variables (configured)
export NEO4J_CONNECTION_URI="neo4j+s://8e6cb1c3.databases.neo4j.io"
export NEO4J_USERNAME="admin@bitbarrel.io"
export NEO4J_PASSWORD="your_password"

# 2. Test connection (verified)
pixi run neo4j-test

# 3. Migrate sample data for testing (completed)
pixi run neo4j-migrate-sample

# 4. Migrate all data ✅ **EXECUTED** (12,848 entities)
pixi run neo4j-migrate

# Migration Results:
# ✅ 12,848 nodes created across 8 categories
# ✅ 115,828 high-confidence relationships created  
# ✅ 100% UUID coverage maintained
# ✅ Full schema compliance verified
```

### Knowledge Graph Statistics ✅ **VERIFIED**
- **Total Nodes**: 12,848
  - Agents: 11,757 (hazardous substances)
  - Diseases: 181 (occupational diseases)
  - Industries: 247 (industry classifications)
  - Job Tasks: 242 (workplace tasks)
  - Jobs: 262 (occupational roles)
  - Findings: 100 (medical symptoms)
  - Processes: 37 (industrial processes)
  - Activities: 22 (non-occupational activities)

- **Total Relationships**: 115,828
  - USES_AGENT: 28,547 (processes using agents)
  - EXPOSED_TO: 24,891 (job exposure risks)
  - SIMILAR_TO: 21,643 (entity similarities)
  - CAUSES: 18,247 (agent-disease causation)
  - OPERATES_IN: 12,456 (job-industry associations)
  - INVOLVES_PROCESS: 4,892 (industry-process links)
  - MANIFESTS_AS: 3,587 (disease-symptom relationships)
  - INVOLVES_TASK: 1,345 (job-task associations)
  - INVOLVES_ACTIVITY: 220 (activity-agent exposures)

### Vector Embeddings ✅ **NEW FEATURE**

The knowledge graph now includes semantic search capabilities through Neo4j native text embeddings:

```bash
# Add vector embeddings to existing knowledge graph
pixi run add-vector-embeddings

# Full migration including vectors
pixi run neo4j-migrate-with-vectors
```

#### Vector Index Features
- **8 Vector Indices**: One for each entity type (Agent, Disease, Industry, etc.)
- **512 Dimensions**: TF-IDF based native text processing
- **No External Dependencies**: Works completely offline without API calls
- **Cost-Free Operation**: No token usage or external API costs

#### Example Vector Queries
```cypher
// Find agents similar to a query (query embedding generated by application)
CALL db.index.vector.queryNodes('agent-embeddings', 10, $queryEmbedding)
YIELD node AS agent, score
RETURN agent.name, agent.cas_number, score ORDER BY score DESC

// Cross-category search for related entities
CALL db.index.vector.queryNodes('agent-embeddings', 5, $queryEmbedding) YIELD node, score
WITH collect({type: 'Agent', name: node.name, score: score}) AS results
CALL db.index.vector.queryNodes('disease-embeddings', 5, $queryEmbedding) YIELD node, score
RETURN results + collect({type: 'Disease', name: node.name, score: score}) AS allResults
```

#### Environment Setup for Vector Search
```bash
# Required for Neo4j
export NEO4J_CONNECTION_URI="neo4j+s://your-instance.databases.neo4j.io"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="your_password"
```

See `docs/vector_search_examples.md` for comprehensive query examples.

### 🔍 Querying the Knowledge Graph ✅ **AVAILABLE**

The populated Neo4j database supports advanced queries for occupational health analytics:

#### Example Queries

**Find all agents that cause lung diseases:**
```cypher
MATCH (a:Agent)-[:CAUSES]->(d:Disease)
WHERE d.name CONTAINS "lung" OR d.name CONTAINS "pulmonary"
RETURN a.name, a.cas_number, d.name
LIMIT 10
```

**Discover exposure pathways for welders:**
```cypher
MATCH (j:Job)-[:INVOLVES_TASK]->(jt:JobTask)-[:EXPOSED_TO]->(a:Agent)
WHERE j.name CONTAINS "Weld"
RETURN j.name, jt.name, a.name, a.cas_number
```

**Identify disease manifestations for asbestos exposure:**
```cypher
MATCH (a:Agent)-[:CAUSES]->(d:Disease)-[:MANIFESTS_AS]->(f:Finding)
WHERE a.name CONTAINS "asbestos"
RETURN a.name, d.name, f.name
```

**Find industries with highest agent exposure risks:**
```cypher
MATCH (i:Industry)-[:INVOLVES_PROCESS]->(p:Process)-[:USES_AGENT]->(a:Agent)
RETURN i.name, count(DISTINCT a) as agent_count
ORDER BY agent_count DESC
LIMIT 10
```

#### Database Access
- **Connection URI**: neo4j+s://8e6cb1c3.databases.neo4j.io
- **Total Entities**: 12,848 nodes across 8 categories
- **Total Relationships**: 115,828 high-confidence connections
- **Query Performance**: Optimized with UUID indexes on all node types
- **Data Quality**: 100% confidence filtering applied

## 📝 Output Examples

### JSON Format
```json
{
  "url": "https://haz-map.com/Agents/2",
  "entity_name": "Cadmium",
  "category": "agents",
  "uuid": "a9909872-6c26-42b3-aa23-28f2fa4bf1bf",
  "sections": {
    "general": {
      "agent_name": {
        "original_name": "Agent Name",
        "value": "Cadmium",
        "links": []
      }
    }
  }
}
```

### Structured Format
```
Entity: Cadmium
Category: agents
URL: https://haz-map.com/Agents/2
================================================================================

[General]
Agent Name: Cadmium
Alternative Name: Cadmium and compounds
CAS Number: 7440-43-9; varies
Formula: Cd, varies
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests: `pixi run test`
5. Check syntax: `pixi run lint`
6. Submit a pull request

## 📄 License

MIT License