#!/usr/bin/env python3
"""
Test Neo4j connection and basic migration functionality.
"""

import os
import sys
from pathlib import Path
import logging

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))
from scripts.neo4j_migration import Neo4jMigrator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_connection():
    """Test basic Neo4j connectivity."""
    uri = os.getenv('NEO4J_CONNECTION_URI')
    username = os.getenv('NEO4J_USERNAME') 
    password = os.getenv('NEO4J_PASSWORD')
    
    if not all([uri, username, password]):
        logger.error("Missing required environment variables")
        return False
        
    migrator = Neo4jMigrator(uri, username, password)
    
    try:
        connected = migrator.test_connection()
        if connected:
            logger.info("✅ Neo4j connection successful")
            
            # Test basic query
            with migrator.driver.session() as session:
                result = session.run("RETURN 'Hello Neo4j' as message")
                message = result.single()["message"]
                logger.info(f"✅ Query test: {message}")
                
            return True
        else:
            logger.error("❌ Neo4j connection failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Connection test error: {e}")
        return False
    finally:
        migrator.close()


def test_small_migration():
    """Test migration with a small subset of data."""
    uri = os.getenv('NEO4J_CONNECTION_URI')
    username = os.getenv('NEO4J_USERNAME')
    password = os.getenv('NEO4J_PASSWORD')
    
    if not all([uri, username, password]):
        logger.error("Missing required environment variables")
        return False
        
    migrator = Neo4jMigrator(uri, username, password)
    
    try:
        # Clear database first
        migrator.clear_database()
        migrator.create_indexes()
        
        # Test with one file from each category
        json_dir = Path("data/formatted/json")
        test_files = []
        
        for category_dir in json_dir.iterdir():
            if category_dir.is_dir():
                json_files = list(category_dir.glob("*.json"))
                if json_files:
                    test_files.append(json_files[0])
                    
        logger.info(f"Testing with {len(test_files)} files")
        
        # Migrate test files
        nodes_created = 0
        for test_file in test_files:
            if migrator.migrate_file(test_file):
                nodes_created += 1
                logger.info(f"✅ Migrated: {test_file.name}")
            else:
                logger.error(f"❌ Failed to migrate: {test_file.name}")
                
        # Create relationships for test files
        relationships_created = 0
        for test_file in test_files:
            data = migrator.load_json_file(test_file)
            if data:
                relationships = migrator.extract_relationships(data)
                with migrator.driver.session() as session:
                    for source_uuid, target_uuid, rel_type, rel_props in relationships:
                        if migrator.create_relationship(session, source_uuid, target_uuid, rel_type, rel_props):
                            relationships_created += 1
                            
        logger.info(f"✅ Test migration complete: {nodes_created} nodes, {relationships_created} relationships")
        
        # Verify data in database
        with migrator.driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) as node_count")
            node_count = result.single()["node_count"]
            
            result = session.run("MATCH ()-[r]->() RETURN count(r) as rel_count")
            rel_count = result.single()["rel_count"]
            
            logger.info(f"✅ Database verification: {node_count} nodes, {rel_count} relationships")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Test migration failed: {e}")
        return False
    finally:
        migrator.close()


if __name__ == "__main__":
    print("Testing Neo4j connection...")
    if test_connection():
        print("\nTesting small migration...")
        test_small_migration()
    else:
        print("Connection test failed - check environment variables")