#!/usr/bin/env python3
"""
Execute the full HazMap Neo4j migration and verify results.

This script performs the complete migration of 12,848 entities
to Neo4j knowledge graph database.
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
import logging

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))
from scripts.neo4j_migration import Neo4jMigrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def count_files_by_category(json_dir: Path):
    """Count JSON files by category."""
    stats = {}
    total = 0
    
    for category_dir in json_dir.iterdir():
        if category_dir.is_dir():
            count = len(list(category_dir.glob("*.json")))
            stats[category_dir.name] = count
            total += count
            
    return stats, total


def analyze_cross_references(json_dir: Path):
    """Analyze cross-references for relationship statistics."""
    relationship_stats = {}
    confidence_1_count = 0
    total_refs = 0
    
    for category_dir in json_dir.iterdir():
        if not category_dir.is_dir():
            continue
            
        for json_file in category_dir.glob("*.json"):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    
                cross_refs = data.get('cross_references', [])
                for ref in cross_refs:
                    total_refs += 1
                    confidence = ref.get('confidence', 0)
                    ref_type = ref.get('type', 'unknown')
                    
                    if confidence == 1.0:
                        confidence_1_count += 1
                        
                    # Count by type
                    if ref_type not in relationship_stats:
                        relationship_stats[ref_type] = {'total': 0, 'confidence_1': 0}
                    relationship_stats[ref_type]['total'] += 1
                    if confidence == 1.0:
                        relationship_stats[ref_type]['confidence_1'] += 1
                        
            except Exception as e:
                logger.warning(f"Error analyzing {json_file}: {e}")
                
    return {
        'total_cross_references': total_refs,
        'confidence_1_count': confidence_1_count,
        'by_type': relationship_stats
    }


def execute_full_migration():
    """Execute the complete migration process."""
    start_time = datetime.now()
    
    # Environment check
    uri = os.getenv('NEO4J_CONNECTION_URI')
    username = os.getenv('NEO4J_USERNAME')
    password = os.getenv('NEO4J_PASSWORD')
    
    if not all([uri, username, password]):
        logger.error("Missing required environment variables: NEO4J_CONNECTION_URI, NEO4J_USERNAME, NEO4J_PASSWORD")
        return False
        
    # Data check
    json_dir = Path("data/formatted/json")
    if not json_dir.exists():
        logger.error(f"JSON directory not found: {json_dir}")
        return False
        
    # Count files and analyze cross-references
    logger.info("Analyzing data before migration...")
    file_stats, total_files = count_files_by_category(json_dir)
    ref_stats = analyze_cross_references(json_dir)
    
    logger.info(f"📊 Pre-migration Analysis:")
    logger.info(f"  Total JSON files: {total_files}")
    for category, count in file_stats.items():
        logger.info(f"  {category}: {count} files")
        
    logger.info(f"  Total cross-references: {ref_stats['total_cross_references']}")
    logger.info(f"  Confidence 1.0 references: {ref_stats['confidence_1_count']}")
    logger.info(f"  Expected relationships to migrate: {ref_stats['confidence_1_count']}")
    
    # Initialize migrator
    logger.info("Initializing Neo4j connection...")
    migrator = Neo4jMigrator(uri, username, password)
    
    try:
        # Test connection
        if not migrator.test_connection():
            logger.error("❌ Cannot connect to Neo4j database")
            return False
            
        logger.info("✅ Connected to Neo4j successfully")
        
        # Execute migration
        logger.info("🚀 Starting full migration...")
        nodes_created, relationships_created = migrator.migrate_all(json_dir, clear_first=True)
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Log results
        logger.info(f"🎉 Migration completed successfully!")
        logger.info(f"📈 Results:")
        logger.info(f"  Nodes created: {nodes_created}")
        logger.info(f"  Relationships created: {relationships_created}")
        logger.info(f"  Duration: {duration}")
        
        # Verify migration
        logger.info("🔍 Verifying migration...")
        verify_results = verify_migration(migrator)
        
        # Generate migration report
        report = {
            'migration_date': start_time.isoformat(),
            'duration_seconds': duration.total_seconds(),
            'input_stats': {
                'total_files': total_files,
                'files_by_category': file_stats,
                'cross_reference_analysis': ref_stats
            },
            'migration_results': {
                'nodes_created': nodes_created,
                'relationships_created': relationships_created
            },
            'verification': verify_results,
            'success': True
        }
        
        # Save report
        with open('migration_report.json', 'w') as f:
            json.dump(report, f, indent=2)
            
        logger.info("📋 Migration report saved to migration_report.json")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False
    finally:
        migrator.close()


def verify_migration(migrator: Neo4jMigrator):
    """Verify the migration results."""
    verification = {}
    
    try:
        with migrator.driver.session() as session:
            # Count total nodes
            result = session.run("MATCH (n) RETURN count(n) as total_nodes")
            verification['total_nodes'] = result.single()["total_nodes"]
            
            # Count nodes by label
            node_counts = {}
            for node_type in ['Agent', 'Disease', 'Process', 'Industry', 'JobTask', 'Job', 'Finding', 'Activity']:
                result = session.run(f"MATCH (n:{node_type}) RETURN count(n) as count")
                node_counts[node_type] = result.single()["count"]
            verification['nodes_by_type'] = node_counts
            
            # Count total relationships
            result = session.run("MATCH ()-[r]->() RETURN count(r) as total_relationships")
            verification['total_relationships'] = result.single()["total_relationships"]
            
            # Count relationships by type
            result = session.run("""
                MATCH ()-[r]->() 
                RETURN type(r) as rel_type, count(r) as count 
                ORDER BY count DESC
            """)
            rel_counts = {record["rel_type"]: record["count"] for record in result}
            verification['relationships_by_type'] = rel_counts
            
            # Sample nodes with UUIDs
            result = session.run("MATCH (n) WHERE n.uuid IS NOT NULL RETURN count(n) as uuid_nodes")
            verification['nodes_with_uuid'] = result.single()["uuid_nodes"]
            
            # Sample relationships with confidence
            result = session.run("MATCH ()-[r]->() WHERE r.confidence = 1.0 RETURN count(r) as conf_1_rels")
            verification['confidence_1_relationships'] = result.single()["conf_1_rels"]
            
        logger.info("✅ Migration verification completed")
        logger.info(f"  Total nodes: {verification['total_nodes']}")
        logger.info(f"  Total relationships: {verification['total_relationships']}")
        logger.info(f"  Nodes with UUIDs: {verification['nodes_with_uuid']}")
        logger.info(f"  Confidence 1.0 relationships: {verification['confidence_1_relationships']}")
        
        return verification
        
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return {'error': str(e)}


if __name__ == "__main__":
    print("🗄️  HazMap Neo4j Full Migration")
    print("=" * 50)
    
    success = execute_full_migration()
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("📋 Check migration_report.json for detailed results")
        print("📝 Check migration.log for detailed logs")
    else:
        print("\n❌ Migration failed!")
        print("📝 Check migration.log for error details")
        
    sys.exit(0 if success else 1)