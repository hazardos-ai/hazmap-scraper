# HazMap Knowledge Graph Schema

## Overview

This document defines the node types and relationship structure for a knowledge graph based on the HazMap occupational health database. The schema is derived from analysis of 12,848 JSON files across 8 entity categories extracted from haz-map.com.

## Data Source Statistics

- **Total Entities**: 12,848 JSON files
- **Categories**: 8 distinct entity types
- **Cross-references**: Extensive linking between entities with confidence scores
- **Metadata**: Rich temporal and source information for each entity

| Category | Count | Description |
|----------|-------|-------------|
| agents | ~21,500 | Hazardous substances, chemicals, and compounds |
| diseases | 428 | Occupational diseases and health conditions |
| processes | 227 | Industrial and manufacturing processes |
| industries | 307 | Industry classifications with NAICS codes |
| job_tasks | 304 | Specific workplace tasks and activities |
| jobs | 493 | Occupational roles and positions |
| findings | 248 | Symptoms and medical findings |
| activities | 39 | Non-occupational activities that involve exposures |

## Node Types and Properties

### 1. Agent Nodes
**Label**: `Agent`

Core properties for hazardous substances and chemicals:

```cypher
CREATE (a:Agent {
  uuid: STRING,                    // Unique identifier (Primary Key)
  name: STRING,                    // Agent name
  cas_number: STRING,              // Chemical Abstracts Service number
  formula: STRING,                 // Chemical formula
  major_category: STRING,          // Categorization (e.g., "Metals", "Solvents")
  minor_category: STRING,          // Sub-categorization
  synonyms: STRING,                // Alternative names
  source_url: STRING,              // Original haz-map.com URL
  scraped_at: DATETIME,           // Data extraction timestamp
  parsed_at: DATETIME,            // Processing timestamp
  
  // Regulatory classifications
  iarc_carcinogen: STRING,         // IARC carcinogenicity status
  ntp_carcinogen: STRING,          // NTP carcinogenicity status  
  acgih_carcinogen: STRING,        // ACGIH carcinogenicity status
  
  // Health effects flags
  fibrogenic: BOOLEAN,             // Causes fibrosis
  chronic_bronchitis: BOOLEAN,     // Causes chronic bronchitis
  methemoglobinemia: BOOLEAN,      // Causes methemoglobinemia
  
  // Physical properties
  half_life: STRING,               // Biological half-life
  appearance: STRING,              // Physical appearance
  odor: STRING                     // Odor characteristics
})
```

### 2. Disease Nodes
**Label**: `Disease`

Properties for occupational diseases and health conditions:

```cypher
CREATE (d:Disease {
  uuid: STRING,                    // Unique identifier (Primary Key)
  name: STRING,                    // Disease/syndrome name
  category: STRING,                // Disease category (e.g., "Airway Disease")
  acute_chronic: STRING,           // Disease progression type
  synonyms: STRING,                // Alternative names
  source_url: STRING,              // Original haz-map.com URL
  scraped_at: DATETIME,           // Data extraction timestamp
  parsed_at: DATETIME,            // Processing timestamp
  
  // Clinical information
  description: STRING,             // Clinical description
  comments: STRING                 // Additional medical notes
})
```

### 3. Process Nodes
**Label**: `Process`

Properties for industrial and manufacturing processes:

```cypher
CREATE (p:Process {
  uuid: STRING,                    // Unique identifier (Primary Key)
  name: STRING,                    // Process name
  description: STRING,             // Process description
  source_url: STRING,              // Original haz-map.com URL
  scraped_at: DATETIME,           // Data extraction timestamp
  parsed_at: DATETIME,            // Processing timestamp
  
  // Process details
  comments: STRING                 // Additional process information
})
```

### 4. Industry Nodes
**Label**: `Industry`

Properties for industry classifications:

```cypher
CREATE (i:Industry {
  uuid: STRING,                    // Unique identifier (Primary Key)
  name: STRING,                    // Industry name
  naics_code: STRING,              // North American Industry Classification code
  category: STRING,                // Industry category (e.g., "Manufacturing")
  description: STRING,             // Industry description
  source_url: STRING,              // Original haz-map.com URL
  scraped_at: DATETIME,           // Data extraction timestamp
  parsed_at: DATETIME,            // Processing timestamp
  
  // Industry details
  comments: STRING                 // Additional industry information
})
```

### 5. JobTask Nodes
**Label**: `JobTask`

Properties for specific workplace tasks:

```cypher
CREATE (jt:JobTask {
  uuid: STRING,                    // Unique identifier (Primary Key)
  name: STRING,                    // Job task name
  description: STRING,             // Task description
  source_url: STRING,              // Original haz-map.com URL
  scraped_at: DATETIME,           // Data extraction timestamp
  parsed_at: DATETIME,            // Processing timestamp
  
  // Task details
  comments: STRING                 // Additional task information
})
```

### 6. Job Nodes
**Label**: `Job`

Properties for occupational roles:

```cypher
CREATE (j:Job {
  uuid: STRING,                    // Unique identifier (Primary Key)
  name: STRING,                    // Job title
  soc_code: STRING,                // Standard Occupational Classification code
  category: STRING,                // Job category (e.g., "Material Moving")
  description: STRING,             // Job description
  source_url: STRING,              // Original haz-map.com URL
  scraped_at: DATETIME,           // Data extraction timestamp
  parsed_at: DATETIME,            // Processing timestamp
  
  // Job details
  comments: STRING                 // Additional job information
})
```

### 7. Finding Nodes
**Label**: `Finding`

Properties for symptoms and medical findings:

```cypher
CREATE (f:Finding {
  uuid: STRING,                    // Unique identifier (Primary Key)
  name: STRING,                    // Symptom/finding name
  category: STRING,                // Finding category (e.g., "Neurological")
  description: STRING,             // Clinical description
  source_url: STRING,              // Original haz-map.com URL
  scraped_at: DATETIME,           // Data extraction timestamp
  parsed_at: DATETIME,            // Processing timestamp
  
  // Clinical details
  comments: STRING                 // Additional clinical information
})
```

### 8. Activity Nodes
**Label**: `Activity`

Properties for non-occupational activities:

```cypher
CREATE (a:Activity {
  uuid: STRING,                    // Unique identifier (Primary Key)
  name: STRING,                    // Activity name
  description: STRING,             // Activity description
  source_url: STRING,              // Original haz-map.com URL
  scraped_at: DATETIME,           // Data extraction timestamp
  parsed_at: DATETIME,            // Processing timestamp
  
  // Activity details
  comments: STRING                 // Additional activity information
})
```

## Relationship Types and Properties

### 1. CAUSES (Agent → Disease)
Represents causal relationship between hazardous agents and diseases.

```cypher
CREATE (agent)-[:CAUSES {
  confidence: FLOAT,               // Confidence score (0.0-1.0)
  reference_type: STRING,          // "name_match" or "url_match"
  source_text: STRING,             // Original text that established the link
  established_date: DATE           // When relationship was established
}]->(disease)
```

**Example**: `(Asbestos)-[:CAUSES]->(Mesothelioma, pleural)`

### 2. MANIFESTS_AS (Disease → Finding)
Links diseases to their symptoms and clinical findings.

```cypher
CREATE (disease)-[:MANIFESTS_AS {
  confidence: FLOAT,
  reference_type: STRING,
  source_text: STRING
}]->(finding)
```

**Example**: `(Asthma, occupational)-[:MANIFESTS_AS]->(dyspnea, exertional)`

### 3. EXPOSED_TO (Job/JobTask → Agent)
Indicates exposure risks for jobs and tasks.

```cypher
CREATE (job_or_task)-[:EXPOSED_TO {
  confidence: FLOAT,
  reference_type: STRING,
  source_text: STRING,
  exposure_level: STRING          // "high", "moderate", "low" if available
}]->(agent)
```

**Example**: `(Welders)-[:EXPOSED_TO]->(Chromium compounds)`

### 4. INVOLVES_TASK (Job → JobTask)
Links jobs to their associated high-risk tasks.

```cypher
CREATE (job)-[:INVOLVES_TASK {
  confidence: FLOAT,
  reference_type: STRING,
  source_text: STRING
}]->(job_task)
```

**Example**: `(Laborers and Freight, Stock, and Material Movers, Hand)-[:INVOLVES_TASK]->(Handle raw goat hair, wool, or hides from endemic area)`

### 5. OPERATES_IN (Job → Industry)
Associates jobs with their industry contexts.

```cypher
CREATE (job)-[:OPERATES_IN {
  confidence: FLOAT,
  reference_type: STRING,
  source_text: STRING
}]->(industry)
```

### 6. INVOLVES_PROCESS (Industry → Process)
Links industries to their characteristic processes.

```cypher
CREATE (industry)-[:INVOLVES_PROCESS {
  confidence: FLOAT,
  reference_type: STRING,
  source_text: STRING
}]->(process)
```

**Example**: `(Primary Aluminum Production)-[:INVOLVES_PROCESS]->(Aluminum production)`

### 7. USES_AGENT (Process → Agent)
Indicates which agents are used in specific processes.

```cypher
CREATE (process)-[:USES_AGENT {
  confidence: FLOAT,
  reference_type: STRING,
  source_text: STRING
}]->(agent)
```

**Example**: `(Gas Welding and Cutting)-[:USES_AGENT]->(Acetylene)`

### 8. INVOLVES_ACTIVITY (Activity → Agent)
Links non-occupational activities to agent exposures.

```cypher
CREATE (activity)-[:INVOLVES_ACTIVITY {
  confidence: FLOAT,
  reference_type: STRING,
  source_text: STRING
}]->(agent)
```

**Example**: `(Smoking cigarettes)-[:INVOLVES_ACTIVITY]->(Cadmium)`

### 9. SIMILAR_TO (Entity → Entity)
Generic relationship for entities of the same type that are related.

```cypher
CREATE (entity1)-[:SIMILAR_TO {
  confidence: FLOAT,
  reference_type: STRING,
  source_text: STRING,
  similarity_reason: STRING       // Why entities are similar
}]->(entity2)
```

## Cross-Reference Metadata

All relationships include metadata derived from the cross-reference analysis:

- **confidence**: Numerical confidence score (1.0 for exact matches)
- **reference_type**: Either "name_match" or "url_match" 
- **source_text**: The original text that established the relationship
- **uuid_source**: UUID of the source entity
- **uuid_target**: UUID of the target entity

## Implementation Guidelines

### 1. Data Loading Strategy

```cypher
// Load nodes first
LOAD CSV WITH HEADERS FROM 'file:///agents.csv' AS row
CREATE (a:Agent {
  uuid: row.uuid,
  name: row.name,
  cas_number: row.cas_number,
  // ... other properties
});

// Create indexes for performance
CREATE INDEX FOR (a:Agent) ON (a.uuid);
CREATE INDEX FOR (d:Disease) ON (d.uuid);
// ... other indexes

// Load relationships
LOAD CSV WITH HEADERS FROM 'file:///relationships.csv' AS row
MATCH (source {uuid: row.source_uuid})
MATCH (target {uuid: row.target_uuid})
CREATE (source)-[r:CAUSES {
  confidence: toFloat(row.confidence),
  reference_type: row.reference_type
}]->(target);
```

### 2. Query Examples

**Find all agents that cause lung cancer:**
```cypher
MATCH (a:Agent)-[:CAUSES]->(d:Disease)
WHERE d.name CONTAINS "lung cancer"
RETURN a.name, a.cas_number, d.name
```

**Find exposure pathways for a specific job:**
```cypher
MATCH (j:Job {name: "Welders"})-[:INVOLVES_TASK]->(jt:JobTask)-[:EXPOSED_TO]->(a:Agent)
RETURN j.name, jt.name, a.name, a.cas_number
```

**Identify disease manifestations:**
```cypher
MATCH (a:Agent)-[:CAUSES]->(d:Disease)-[:MANIFESTS_AS]->(f:Finding)
WHERE a.name = "Asbestos"
RETURN d.name, f.name, f.category
```

### 3. Data Quality Considerations

- **UUID Integrity**: All UUIDs are unique and stable across data updates
- **Confidence Scoring**: Relationships include confidence metrics for reliability assessment
- **Temporal Data**: Timestamps enable tracking of data freshness and changes
- **Source Attribution**: All entities link back to original haz-map.com sources
- **Cross-validation**: Bidirectional relationships can be validated for consistency

## Schema Evolution

### Version 1.0 (Current)
- Basic node types and relationships
- Cross-reference derived connections
- Confidence scoring
- Source attribution

### Planned Enhancements

#### Version 1.1
- **Exposure Level Quantification**: Add numerical exposure limits and measurements
- **Regulatory Status**: Expand regulatory classification properties
- **Geographic Context**: Add location-specific exposure data
- **Temporal Analysis**: Historical trends in exposure and disease patterns

#### Version 1.2
- **Risk Assessment**: Quantitative risk scoring relationships
- **Intervention Tracking**: Control measures and their effectiveness
- **Literature Integration**: Direct links to research publications
- **Industry Standards**: Integration with OSHA, NIOSH, and other regulatory data

## Data Lineage and Quality

### Source Attribution
- **Primary Source**: haz-map.com occupational health database
- **Extraction Date**: 2025-07-23 to 2025-07-24
- **Processing Method**: Automated scraping with cross-reference analysis
- **Quality Assurance**: Multi-layer validation and confidence scoring

### Update Strategy
- **Frequency**: Weekly automated updates via GitHub Actions
- **Change Detection**: Compare entity hashes to identify modifications
- **Version Control**: Git-based tracking of all schema and data changes
- **Rollback Capability**: Maintain previous versions for data recovery

This schema provides a comprehensive foundation for building a knowledge graph that captures the complex relationships in occupational health data, enabling advanced analytics, risk assessment, and decision support applications.