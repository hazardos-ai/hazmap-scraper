#!/usr/bin/env python3
"""
HazMap Neo4j Migration Script

Migrates JSON data from the HazMap scraper to a Neo4j database.
Implements the graph schema defined in hazmap-graph-schema.md.
Only includes relationships with confidence score of 1.0.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime
import logging

import neo4j
from neo4j import GraphDatabase


# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Neo4jMigrator:
    """Migrates HazMap JSON data to Neo4j database."""
    
    def __init__(self, uri: str, username: str, password: str):
        """Initialize Neo4j connection."""
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
        self.category_mappings = {
            'agents': 'Agent',
            'diseases': 'Disease', 
            'processes': 'Process',
            'industries': 'Industry',
            'job_tasks': 'JobTask',
            'jobs': 'Job',
            'findings': 'Finding',
            'activities': 'Activity'
        }
        
    def close(self):
        """Close Neo4j connection."""
        self.driver.close()
        
    def test_connection(self) -> bool:
        """Test database connectivity."""
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                return result.single()["test"] == 1
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
            
    def create_indexes(self):
        """Create database indexes for performance."""
        indexes = [
            "CREATE INDEX entity_uuid IF NOT EXISTS FOR (n:Agent) ON (n.uuid)",
            "CREATE INDEX entity_uuid IF NOT EXISTS FOR (n:Disease) ON (n.uuid)",
            "CREATE INDEX entity_uuid IF NOT EXISTS FOR (n:Process) ON (n.uuid)",
            "CREATE INDEX entity_uuid IF NOT EXISTS FOR (n:Industry) ON (n.uuid)",
            "CREATE INDEX entity_uuid IF NOT EXISTS FOR (n:JobTask) ON (n.uuid)",
            "CREATE INDEX entity_uuid IF NOT EXISTS FOR (n:Job) ON (n.uuid)",
            "CREATE INDEX entity_uuid IF NOT EXISTS FOR (n:Finding) ON (n.uuid)",
            "CREATE INDEX entity_uuid IF NOT EXISTS FOR (n:Activity) ON (n.uuid)",
        ]
        
        with self.driver.session() as session:
            for index_query in indexes:
                try:
                    session.run(index_query)
                    logger.info(f"Created index: {index_query}")
                except Exception as e:
                    logger.warning(f"Index creation failed (may already exist): {e}")
                    
    def clear_database(self):
        """Clear all nodes and relationships (use with caution)."""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            logger.info("Database cleared")
            
    def load_json_file(self, file_path: Path) -> Optional[Dict]:
        """Load and parse a JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load {file_path}: {e}")
            return None
            
    def extract_node_properties(self, data: Dict, category: str) -> Dict:
        """Extract node properties from JSON data based on category."""
        metadata = data.get('metadata', {})
        sections = data.get('sections', {})
        
        # Base properties for all nodes
        properties = {
            'uuid': metadata.get('uuid'),
            'name': metadata.get('entity_name'),
            'source_url': metadata.get('scraped_from'),
            'scraped_at': metadata.get('scraped_at'),
            'parsed_at': data.get('parsed_at'),
        }
        
        # Category-specific property extraction
        general = sections.get('general', {})
        
        if category == 'agents':
            # Extract agent-specific properties
            properties.update({
                'cas_number': self._extract_field_value(general, 'cas_number'),
                'formula': self._extract_field_value(general, 'formula'),
                'major_category': self._extract_field_value(general, 'major_category'),
                'minor_category': self._extract_field_value(general, 'minor_category'),
                'synonyms': self._extract_field_value(general, 'synonyms'),
                'iarc_carcinogen': self._extract_field_value(general, 'iarc_carcinogen'),
                'ntp_carcinogen': self._extract_field_value(general, 'ntp_carcinogen'),
                'acgih_carcinogen': self._extract_field_value(general, 'acgih_carcinogen'),
                'fibrogenic': self._extract_boolean_field(general, 'fibrogenic'),
                'chronic_bronchitis': self._extract_boolean_field(general, 'chronic_bronchitis'),
                'methemoglobinemia': self._extract_boolean_field(general, 'methemoglobinemia'),
                'half_life': self._extract_field_value(general, 'half_life'),
                'appearance': self._extract_field_value(general, 'appearance'),
                'odor': self._extract_field_value(general, 'odor'),
            })
        elif category == 'diseases':
            properties.update({
                'category': self._extract_field_value(general, 'category'),
                'acute_chronic': self._extract_field_value(general, 'acute_chronic'),
                'synonyms': self._extract_field_value(general, 'synonyms'),
                'description': self._extract_field_value(general, 'description'),
                'comments': self._extract_field_value(general, 'comments'),
            })
        elif category == 'industries':
            properties.update({
                'naics_code': self._extract_field_value(general, 'naics_code'),
                'category': self._extract_field_value(general, 'category'),
                'description': self._extract_field_value(general, 'description'),
                'comments': self._extract_field_value(general, 'comments'),
            })
        elif category == 'jobs':
            properties.update({
                'soc_code': self._extract_field_value(general, 'soc_code'),
                'category': self._extract_field_value(general, 'category'),
                'description': self._extract_field_value(general, 'description'),
                'comments': self._extract_field_value(general, 'comments'),
            })
        else:
            # For other categories (processes, job_tasks, findings, activities)
            properties.update({
                'description': self._extract_field_value(general, 'description'),
                'comments': self._extract_field_value(general, 'comments'),
                'category': self._extract_field_value(general, 'category'),
            })
            
        # Remove None values
        return {k: v for k, v in properties.items() if v is not None}
        
    def _extract_field_value(self, section: Dict, field_name: str) -> Optional[str]:
        """Extract field value from a section."""
        field = section.get(field_name, {})
        if isinstance(field, dict):
            return field.get('value')
        return field
        
    def _extract_boolean_field(self, section: Dict, field_name: str) -> Optional[bool]:
        """Extract boolean field from a section."""
        value = self._extract_field_value(section, field_name)
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', 'yes', '1', 'on')
        return bool(value)
        
    def create_node(self, session, category: str, properties: Dict) -> bool:
        """Create a node in the database."""
        label = self.category_mappings.get(category)
        if not label:
            logger.error(f"Unknown category: {category}")
            return False
            
        # Build property string for Cypher query
        prop_items = []
        for key, value in properties.items():
            if value is not None:
                if isinstance(value, str):
                    # Escape single quotes in strings
                    escaped_value = value.replace("'", "\\'")
                    prop_items.append(f"{key}: '{escaped_value}'")
                elif isinstance(value, bool):
                    prop_items.append(f"{key}: {str(value).lower()}")
                else:
                    prop_items.append(f"{key}: '{value}'")
                    
        prop_string = ", ".join(prop_items)
        
        query = f"CREATE (n:{label} {{{prop_string}}})"
        
        try:
            session.run(query)
            return True
        except Exception as e:
            logger.error(f"Failed to create {label} node: {e}")
            logger.error(f"Query: {query}")
            return False
            
    def extract_relationships(self, data: Dict) -> List[Tuple[str, str, str, Dict]]:
        """Extract relationships from cross-references with confidence 1.0."""
        relationships = []
        cross_references = data.get('cross_references', [])
        source_uuid = data.get('metadata', {}).get('uuid')
        source_category = data.get('metadata', {}).get('category')
        
        if not source_uuid or not source_category:
            return relationships
            
        for ref in cross_references:
            # Only process name_match relationships with confidence 1.0
            if (ref.get('type') == 'name_match' and 
                ref.get('confidence') == 1.0 and 
                ref.get('uuid') and 
                ref.get('category')):
                
                target_uuid = ref['uuid']
                target_category = ref['category']
                
                # Determine relationship type based on categories
                rel_type = self._determine_relationship_type(source_category, target_category)
                
                if rel_type:
                    rel_props = {
                        'confidence': ref['confidence'],
                        'reference_type': ref['type'],
                        'source_text': ref.get('text', ''),
                        'established_date': datetime.now().date().isoformat()
                    }
                    
                    relationships.append((source_uuid, target_uuid, rel_type, rel_props))
                    
        return relationships
        
    def _determine_relationship_type(self, source_category: str, target_category: str) -> Optional[str]:
        """Determine relationship type based on source and target categories."""
        # Define relationship mappings based on the schema
        mappings = {
            ('agents', 'diseases'): 'CAUSES',
            ('diseases', 'findings'): 'MANIFESTS_AS',
            ('jobs', 'agents'): 'EXPOSED_TO',
            ('job_tasks', 'agents'): 'EXPOSED_TO',
            ('jobs', 'job_tasks'): 'INVOLVES_TASK',
            ('jobs', 'industries'): 'OPERATES_IN',
            ('industries', 'processes'): 'INVOLVES_PROCESS',
            ('processes', 'agents'): 'USES_AGENT',
            ('activities', 'agents'): 'INVOLVES_ACTIVITY',
        }
        
        # Check direct mapping
        rel_type = mappings.get((source_category, target_category))
        if rel_type:
            return rel_type
            
        # For same-category relationships, use SIMILAR_TO
        if source_category == target_category:
            return 'SIMILAR_TO'
            
        return None
        
    def create_relationship(self, session, source_uuid: str, target_uuid: str, 
                          rel_type: str, properties: Dict) -> bool:
        """Create a relationship between two nodes."""
        # Build property string
        prop_items = []
        for key, value in properties.items():
            if value is not None:
                if isinstance(value, str):
                    escaped_value = value.replace("'", "\\'")
                    prop_items.append(f"{key}: '{escaped_value}'")
                elif isinstance(value, (int, float)):
                    prop_items.append(f"{key}: {value}")
                else:
                    prop_items.append(f"{key}: '{value}'")
                    
        prop_string = ", ".join(prop_items)
        prop_clause = f" {{{prop_string}}}" if prop_string else ""
        
        query = f"""
        MATCH (source {{uuid: '{source_uuid}'}})
        MATCH (target {{uuid: '{target_uuid}'}})
        CREATE (source)-[r:{rel_type}{prop_clause}]->(target)
        """
        
        try:
            session.run(query)
            return True
        except Exception as e:
            logger.error(f"Failed to create {rel_type} relationship: {e}")
            logger.error(f"Query: {query}")
            return False
            
    def migrate_file(self, file_path: Path) -> bool:
        """Migrate a single JSON file to Neo4j."""
        data = self.load_json_file(file_path)
        if not data:
            return False
            
        category = data.get('metadata', {}).get('category')
        if not category:
            logger.error(f"No category found in {file_path}")
            return False
            
        with self.driver.session() as session:
            # Create node
            properties = self.extract_node_properties(data, category)
            if not self.create_node(session, category, properties):
                return False
                
            logger.debug(f"Created {category} node: {properties.get('name')}")
            
        return True
        
    def migrate_relationships(self, json_dir: Path) -> int:
        """Create relationships after all nodes are created."""
        relationships_created = 0
        
        for category_dir in json_dir.iterdir():
            if not category_dir.is_dir():
                continue
                
            category = category_dir.name
            logger.info(f"Processing relationships for category: {category}")
            
            for json_file in category_dir.glob("*.json"):
                data = self.load_json_file(json_file)
                if not data:
                    continue
                    
                relationships = self.extract_relationships(data)
                
                with self.driver.session() as session:
                    for source_uuid, target_uuid, rel_type, rel_props in relationships:
                        if self.create_relationship(session, source_uuid, target_uuid, rel_type, rel_props):
                            relationships_created += 1
                            
        return relationships_created
        
    def migrate_all(self, json_dir: Path, clear_first: bool = False, include_vectors: bool = False) -> Tuple[int, int]:
        """Migrate all JSON files to Neo4j."""
        if clear_first:
            self.clear_database()
            
        self.create_indexes()
        
        nodes_created = 0
        
        # First pass: Create all nodes
        logger.info("Creating nodes...")
        for category_dir in json_dir.iterdir():
            if not category_dir.is_dir():
                continue
                
            category = category_dir.name
            logger.info(f"Processing category: {category}")
            
            for json_file in category_dir.glob("*.json"):
                if self.migrate_file(json_file):
                    nodes_created += 1
                    
                if nodes_created % 100 == 0:
                    logger.info(f"Created {nodes_created} nodes...")
                    
        logger.info(f"Completed node creation: {nodes_created} nodes")
        
        # Second pass: Create relationships
        logger.info("Creating relationships...")
        relationships_created = self.migrate_relationships(json_dir)
        
        logger.info(f"Migration complete: {nodes_created} nodes, {relationships_created} relationships")
        
        # Third pass: Add vector embeddings (AFTER relationships are complete)
        if include_vectors:
            logger.info("Adding vector embeddings...")
            try:
                from .vector_embeddings import VectorEmbedder
                
                # Get connection details
                uri = os.getenv('NEO4J_CONNECTION_URI')
                username = os.getenv('NEO4J_USERNAME') 
                password = os.getenv('NEO4J_PASSWORD')
                openai_api_key = os.getenv('OPENAI_API_KEY')
                
                embedder = VectorEmbedder(uri, username, password, openai_api_key)
                
                # Use mock embeddings if OpenAI API key is not available
                use_mock = not openai_api_key
                if use_mock:
                    logger.warning("OpenAI API key not found, using mock embeddings")
                
                # Create vector indices
                embedder.create_vector_indices()
                
                # Generate embeddings for all entities
                embedding_stats = embedder.process_json_files_for_embeddings(json_dir, use_mock=use_mock)
                
                embedder.close()
                
                logger.info("Vector embeddings completed!")
                for category, count in embedding_stats.items():
                    logger.info(f"  {category}: {count} embeddings generated")
                    
            except ImportError:
                logger.error("Vector embeddings module not found")
            except Exception as e:
                logger.error(f"Vector embedding generation failed: {e}")
        
        return nodes_created, relationships_created


def main():
    """Main migration function."""
    # Get environment variables
    uri = os.getenv('NEO4J_CONNECTION_URI')
    username = os.getenv('NEO4J_USERNAME')
    password = os.getenv('NEO4J_PASSWORD')
    
    if not all([uri, username, password]):
        logger.error("Missing required environment variables: NEO4J_CONNECTION_URI, NEO4J_USERNAME, NEO4J_PASSWORD")
        sys.exit(1)
        
    # Check if vector embeddings should be included
    include_vectors = os.getenv('INCLUDE_VECTOR_EMBEDDINGS', 'false').lower() == 'true'
    
    # Set up paths
    json_dir = Path("data/formatted/json")
    if not json_dir.exists():
        logger.error(f"JSON directory not found: {json_dir}")
        sys.exit(1)
        
    # Initialize migrator
    migrator = Neo4jMigrator(uri, username, password)
    
    try:
        # Test connection
        if not migrator.test_connection():
            logger.error("Cannot connect to Neo4j database")
            sys.exit(1)
            
        logger.info("Connected to Neo4j successfully")
        
        # Migrate data (including vector embeddings if requested)
        nodes_created, relationships_created = migrator.migrate_all(
            json_dir, 
            clear_first=True, 
            include_vectors=include_vectors
        )
        
        logger.info(f"Migration successful: {nodes_created} nodes, {relationships_created} relationships")
        if include_vectors:
            logger.info("Vector embeddings have been added to the knowledge graph")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        sys.exit(1)
    finally:
        migrator.close()


if __name__ == "__main__":
    main()