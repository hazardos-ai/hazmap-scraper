#!/usr/bin/env python3
"""
Neo4j Sample Migration Script

Migrates a sample of JSON data for testing purposes.
Uses NEO4J_SAMPLE_SIZE environment variable to control sample size (default: 100).
"""

import os
import sys
import random
from pathlib import Path
import logging

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from scripts.neo4j_migration import Neo4jMigrator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """Sample migration function."""
    # Get environment variables
    uri = os.getenv('NEO4J_CONNECTION_URI')
    username = os.getenv('NEO4J_USERNAME')
    password = os.getenv('NEO4J_PASSWORD')
    sample_size = int(os.getenv('NEO4J_SAMPLE_SIZE', '100'))
    
    if not all([uri, username, password]):
        logger.error("Missing required environment variables: NEO4J_CONNECTION_URI, NEO4J_USERNAME, NEO4J_PASSWORD")
        sys.exit(1)
        
    # Set up paths
    json_dir = Path("data/formatted/json")
    if not json_dir.exists():
        logger.error(f"JSON directory not found: {json_dir}")
        sys.exit(1)
        
    # Collect all JSON files
    all_files = []
    for category_dir in json_dir.iterdir():
        if category_dir.is_dir():
            all_files.extend(list(category_dir.glob("*.json")))
            
    logger.info(f"Found {len(all_files)} total JSON files")
    
    # Sample files
    sample_files = random.sample(all_files, min(sample_size, len(all_files)))
    logger.info(f"Using sample of {len(sample_files)} files")
    
    # Initialize migrator
    migrator = Neo4jMigrator(uri, username, password)
    
    try:
        # Test connection
        if not migrator.test_connection():
            logger.error("Cannot connect to Neo4j database")
            sys.exit(1)
            
        logger.info("Connected to Neo4j successfully")
        
        # Clear database and create indexes
        migrator.clear_database()
        migrator.create_indexes()
        
        # Migrate sample files
        nodes_created = 0
        for file_path in sample_files:
            if migrator.migrate_file(file_path):
                nodes_created += 1
                if nodes_created % 10 == 0:
                    logger.info(f"Created {nodes_created} nodes...")
                    
        logger.info(f"Completed node creation: {nodes_created} nodes")
        
        # Create relationships for sample files
        relationships_created = 0
        for file_path in sample_files:
            data = migrator.load_json_file(file_path)
            if data:
                relationships = migrator.extract_relationships(data)
                with migrator.driver.session() as session:
                    for source_uuid, target_uuid, rel_type, rel_props in relationships:
                        if migrator.create_relationship(session, source_uuid, target_uuid, rel_type, rel_props):
                            relationships_created += 1
                            
        logger.info(f"Sample migration complete: {nodes_created} nodes, {relationships_created} relationships")
        
        # Verify data
        with migrator.driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) as node_count")
            node_count = result.single()["node_count"]
            
            result = session.run("MATCH ()-[r]->() RETURN count(r) as rel_count")
            rel_count = result.single()["rel_count"]
            
            logger.info(f"Database verification: {node_count} nodes, {rel_count} relationships")
        
    except Exception as e:
        logger.error(f"Sample migration failed: {e}")
        sys.exit(1)
    finally:
        migrator.close()


if __name__ == "__main__":
    main()