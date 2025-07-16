# HazMap Registry Scraper

An automated scraper for extracting entity data from haz-map.com to build a UUID-based registry for Neo4j knowledge graph construction.

## Features

- ✅ **Smart Filtering**: Automatically skips invalid entries like "| Haz-Map"
- ✅ **Timestamped Files**: Creates separate registry files for each category with timestamps
- ✅ **Progress Tracking**: Shows real-time progress during scraping
- ✅ **Duplicate Prevention**: Checks for existing registry files before scraping
- ✅ **GitHub Actions Integration**: Automated scraping via GitHub Actions
- ✅ **UUID Generation**: Unique identifiers for all entities
- ✅ **Rate Limiting**: Respectful delays between requests

## Registry Files

Registry files are saved in the `data/` directory with the following naming convention:
```
{category}_registry_{timestamp}.yml
```

Example files:
- `activities_registry_20250716_120000.yml`
- `agents_registry_20250716_120100.yml`
- `diseases_registry_20250716_120200.yml`
- `findings_registry_20250716_120300.yml`
- `industries_registry_20250716_120400.yml`
- `job_tasks_registry_20250716_120500.yml`
- `jobs_registry_20250716_120600.yml`
- `processes_registry_20250716_120700.yml`

## Registry File Format

Each registry file contains:
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

## Configuration

The scraper uses `src/models/sitemap.yml` to define the categories to scrape:

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

## Usage

### Manual Execution
```bash
# Install dependencies
pixi install

# Run the scraper
pixi run python src/scripts/scrape_registry.py
```

### GitHub Actions
The scraper runs automatically via GitHub Actions:
- **Schedule**: Weekly on Sundays at 2 AM UTC
- **Manual**: Use the "Run workflow" button in the Actions tab

## Data Models

The scraper uses Pydantic models for data validation:

### EntityEntry
```python
class EntityEntry(BaseModel):
    uuid: str
    name: str
    url: str
```

### CategoryRegistry
```python
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

## Error Handling

The scraper includes robust error handling:
- **Invalid Entries**: Skips "| Haz-Map" placeholder entries
- **Server Errors**: Logs and continues processing
- **Rate Limiting**: Implements delays between requests
- **Duplicate Prevention**: Checks for existing registry files

## File Structure

```
hazmap-scraper/
├── data/                          # Generated registry files
│   ├── activities_registry_*.yml
│   ├── agents_registry_*.yml
│   └── ...
├── src/
│   ├── models/
│   │   ├── registry.py           # Pydantic models
│   │   └── sitemap.yml           # Scraping configuration
│   └── scripts/
│       └── scrape_registry.py    # Main scraper
├── tests/                        # Test files
├── .github/workflows/
│   └── scrape-registry.yml      # GitHub Actions workflow
└── pyproject.toml               # Dependencies
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run tests: `pixi run pytest`
6. Submit a pull request

## License

MIT License