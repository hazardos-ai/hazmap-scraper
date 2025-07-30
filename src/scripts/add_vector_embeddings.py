#!/usr/bin/env python3
"""
Vector Embeddings Migration Script

This script adds vector embeddings to an existing HazMap knowledge graph.
It should be run AFTER all nodes and relationships have been created.

Usage:
    python src/scripts/add_vector_embeddings.py [--mock]
    
Arguments:
    --mock    Use mock embeddings instead of OpenAI API (for testing)
"""

import argparse
import os
import sys
from pathlib import Path
import logging

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from scripts.vector_embeddings import VectorEmbedder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main function for adding vector embeddings to existing knowledge graph."""
    parser = argparse.ArgumentParser(description='Add vector embeddings to HazMap knowledge graph')
    parser.add_argument('--mock', action='store_true', 
                        help='Use mock embeddings instead of OpenAI API')
    args = parser.parse_args()
    
    # Get environment variables
    neo4j_uri = os.getenv('NEO4J_CONNECTION_URI')
    neo4j_username = os.getenv('NEO4J_USERNAME')
    neo4j_password = os.getenv('NEO4J_PASSWORD')
    openai_api_key = os.getenv('OPENAI_API_KEY')
    
    if not all([neo4j_uri, neo4j_username, neo4j_password]):
        logger.error("Missing required Neo4j environment variables:")
        logger.error("  NEO4J_CONNECTION_URI")
        logger.error("  NEO4J_USERNAME") 
        logger.error("  NEO4J_PASSWORD")
        sys.exit(1)
        
    # Check if we should use mock embeddings
    use_mock = args.mock or not openai_api_key
    if use_mock and not args.mock:
        logger.warning("OpenAI API key not found, using mock embeddings")
    elif args.mock:
        logger.info("Using mock embeddings as requested")
    
    # Set up paths
    json_dir = Path("data/formatted/json")
    if not json_dir.exists():
        logger.error(f"JSON directory not found: {json_dir}")
        sys.exit(1)
        
    # Initialize embedder
    embedder = VectorEmbedder(neo4j_uri, neo4j_username, neo4j_password, openai_api_key)
    
    try:
        # Test connection
        if not embedder.test_connection():
            logger.error("Cannot connect to Neo4j database")
            sys.exit(1)
            
        logger.info("Connected to Neo4j successfully")
        
        # Get initial statistics
        logger.info("Getting initial embedding statistics...")
        initial_stats = embedder.get_embedding_statistics()
        logger.info("Initial state:")
        for category, data in initial_stats.items():
            total = data.get('total_nodes', 0)
            with_embeddings = data.get('nodes_with_embeddings', 0)
            without_embeddings = data.get('nodes_without_embeddings', 0)
            logger.info(f"  {category}: {total} total, {with_embeddings} with embeddings, {without_embeddings} without")
        
        # Create vector indices
        logger.info("Creating vector indices...")
        embedder.create_vector_indices()
        
        # Process all JSON files to generate embeddings
        logger.info("Generating embeddings for all entities...")
        stats = embedder.process_json_files_for_embeddings(json_dir, use_mock=use_mock)
        
        logger.info("Embedding generation complete!")
        logger.info("Processing statistics:")
        total_processed = 0
        for category, count in stats.items():
            logger.info(f"  {category}: {count} embeddings generated")
            total_processed += count
            
        # Get final statistics
        logger.info("Getting final embedding statistics...")
        final_stats = embedder.get_embedding_statistics()
        logger.info("Final state:")
        for category, data in final_stats.items():
            total = data.get('total_nodes', 0)
            with_embeddings = data.get('nodes_with_embeddings', 0)
            without_embeddings = data.get('nodes_without_embeddings', 0)
            logger.info(f"  {category}: {total} total, {with_embeddings} with embeddings, {without_embeddings} without")
            
        logger.info(f"\nVector embedding migration completed successfully!")
        logger.info(f"Total embeddings processed: {total_processed}")
        
        # Test vector search functionality
        logger.info("\nTesting vector search functionality...")
        test_queries = [
            ("asbestos", "agents"),
            ("lung cancer", "diseases"), 
            ("mining", "industries")
        ]
        
        for query_text, category in test_queries:
            logger.info(f"Testing search for '{query_text}' in {category}...")
            results = embedder.query_similar_entities(query_text, category, limit=3, use_mock=use_mock)
            if results:
                logger.info(f"  Found {len(results)} similar entities:")
                for result in results:
                    logger.info(f"    {result.get('name', 'Unknown')} (score: {result.get('score', 0):.4f})")
            else:
                logger.warning(f"  No results found for '{query_text}' in {category}")
        
    except Exception as e:
        logger.error(f"Vector embedding migration failed: {e}")
        sys.exit(1)
    finally:
        embedder.close()


if __name__ == "__main__":
    main()