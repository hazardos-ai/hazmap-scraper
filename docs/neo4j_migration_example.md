# Neo4j Migration - Example Usage

This document provides a complete example of using the Neo4j migration functionality.

## Prerequisites

1. **Neo4j Database**: You need a running Neo4j instance
2. **Environment Variables**: Set the required Neo4j connection details
3. **JSON Data**: Ensure the scraped JSON data exists in `data/formatted/json/`

## Environment Setup

```bash
# Set your Neo4j connection details
export NEO4J_CONNECTION_URI="bolt://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="your_password"

# Optional: HTTP API URL
export NEO4J_QUERY_API_URL="http://localhost:7474"
```

## Basic Usage

### 1. Test Connection
```bash
# Test if you can connect to Neo4j
python src/scripts/test_neo4j.py
```

Expected output:
```
✅ Neo4j connection successful
✅ Query test: Hello Neo4j
```

### 2. Sample Migration
```bash
# Migrate a small sample (100 entities by default)
python src/scripts/neo4j_migration_sample.py
```

Expected output:
```
2025-07-29 - INFO - Found 12848 total JSON files
2025-07-29 - INFO - Using sample of 100 files
2025-07-29 - INFO - Connected to Neo4j successfully
2025-07-29 - INFO - Created 10 nodes...
2025-07-29 - INFO - Completed node creation: 100 nodes
2025-07-29 - INFO - Sample migration complete: 100 nodes, 45 relationships
2025-07-29 - INFO - Database verification: 100 nodes, 45 relationships
```

### 3. Full Migration
```bash
# Migrate all 12,848 entities
python src/scripts/neo4j_migration.py
```

## Verification Queries

After migration, you can verify the data in Neo4j:

### Check Node Counts
```cypher
MATCH (n) RETURN labels(n)[0] as nodeType, count(n) as count ORDER BY count DESC
```

### Check Relationship Types
```cypher
MATCH ()-[r]->() RETURN type(r) as relType, count(r) as count ORDER BY count DESC
```

### Find Agents that Cause Diseases
```cypher
MATCH (a:Agent)-[:CAUSES]->(d:Disease)
RETURN a.name, d.name
LIMIT 10
```

### Find Job Exposures
```cypher
MATCH (j:Job)-[:EXPOSED_TO]->(a:Agent)
RETURN j.name, a.name, a.cas_number
LIMIT 10
```

## Data Quality

The migration includes confidence filtering:
- Only relationships with `confidence = 1.0` are migrated
- Only `name_match` reference types are processed
- All nodes include source URLs and timestamps

## Performance

- **Sample migration (100 entities)**: ~10 seconds
- **Full migration (12,848 entities)**: ~10-15 minutes
- **Database size**: ~50MB for complete dataset

## Troubleshooting

### Connection Issues
```bash
# Test basic connectivity
python -c "
import neo4j
driver = neo4j.GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password'))
with driver.session() as session:
    result = session.run('RETURN 1')
    print('Connected successfully')
driver.close()
"
```

### Missing Data
If no relationships are created, check:
1. JSON files contain `cross_references` with `confidence: 1.0`
2. Environment variables are set correctly
3. Check logs for error messages

### Performance Issues
For large migrations:
- Use sample migration first to test
- Monitor Neo4j memory usage
- Consider batch size adjustments in the script