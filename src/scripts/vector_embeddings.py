#!/usr/bin/env python3
"""
Vector Embeddings Module for HazMap Knowledge Graph

This module provides functionality to:
1. Generate vector embeddings for text content using Neo4j's native text processing
2. Create vector indices in Neo4j database
3. Update existing nodes with embedding properties
4. Provide vector similarity search capabilities

This should be run AFTER all nodes and relationships have been created.
"""

import json
import os
import sys
import time
import re
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
from datetime import datetime
from collections import Counter

import neo4j
from neo4j import GraphDatabase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VectorEmbedder:
    """Handles vector embeddings for HazMap knowledge graph using Neo4j native text processing."""
    
    def __init__(self, neo4j_uri: str, neo4j_username: str, neo4j_password: str, 
                 test_mode: bool = False):
        """Initialize the vector embedder."""
        self.test_mode = test_mode
        if not test_mode:
            self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_username, neo4j_password))
        else:
            self.driver = None
        
        # Categories that should have vector embeddings
        self.embeddable_categories = {
            'agents': 'Agent',
            'diseases': 'Disease', 
            'industries': 'Industry',
            'jobs': 'Job',
            'processes': 'Process',
            'job_tasks': 'JobTask',
            'findings': 'Finding',
            'activities': 'Activity'
        }
        
        # Vector index configurations - using smaller dimensions for simple embeddings
        self.vector_configs = {
            'agents': {
                'index_name': 'agent-embeddings',
                'property': 'embedding',
                'dimensions': 512,  # Reduced from 1536 for simpler embeddings
                'similarity_function': 'cosine'
            },
            'diseases': {
                'index_name': 'disease-embeddings', 
                'property': 'embedding',
                'dimensions': 512,
                'similarity_function': 'cosine'
            },
            'industries': {
                'index_name': 'industry-embeddings',
                'property': 'embedding', 
                'dimensions': 512,
                'similarity_function': 'cosine'
            },
            'jobs': {
                'index_name': 'job-embeddings',
                'property': 'embedding',
                'dimensions': 512, 
                'similarity_function': 'cosine'
            },
            'processes': {
                'index_name': 'process-embeddings',
                'property': 'embedding',
                'dimensions': 512,
                'similarity_function': 'cosine'
            },
            'job_tasks': {
                'index_name': 'jobtask-embeddings',
                'property': 'embedding',
                'dimensions': 512,
                'similarity_function': 'cosine'
            },
            'findings': {
                'index_name': 'finding-embeddings',
                'property': 'embedding',
                'dimensions': 512,
                'similarity_function': 'cosine'
            },
            'activities': {
                'index_name': 'activity-embeddings',
                'property': 'embedding',
                'dimensions': 512,
                'similarity_function': 'cosine'
            }
        }
        
        # Vocabulary for text vectorization (will be built from data)
        self.vocabulary = set()
        self.vocabulary_built = False
        
    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()
            
    def test_connection(self) -> bool:
        """Test database connectivity."""
        if self.test_mode:
            return True
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1 as test")
                return result.single()["test"] == 1
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
            
    def extract_text_content(self, data: Dict, category: str) -> str:
        """Extract text content from JSON data for embedding generation."""
        metadata = data.get('metadata', {})
        sections = data.get('sections', {})
        general = sections.get('general', {})
        
        # Start with entity name
        text_parts = []
        entity_name = metadata.get('entity_name', '')
        if entity_name:
            text_parts.append(entity_name)
            
        # Add category-specific content
        if category == 'agents':
            # For agents, include synonyms and description
            synonyms = self._extract_field_value(general, 'synonyms')
            if synonyms:
                text_parts.append(f"Synonyms: {synonyms}")
                
            major_category = self._extract_field_value(general, 'major_category')
            if major_category:
                text_parts.append(f"Category: {major_category}")
                
            minor_category = self._extract_field_value(general, 'minor_category')
            if minor_category:
                text_parts.append(f"Type: {minor_category}")
                
        elif category == 'diseases':
            # For diseases, include description and category
            description = self._extract_field_value(general, 'description')
            if description:
                text_parts.append(description)
                
            disease_category = self._extract_field_value(general, 'category')
            if disease_category:
                text_parts.append(f"Category: {disease_category}")
                
            synonyms = self._extract_field_value(general, 'synonyms')
            if synonyms:
                text_parts.append(f"Synonyms: {synonyms}")
                
        elif category == 'industries':
            # For industries, include description and NAICS code
            description = self._extract_field_value(general, 'description')
            if description:
                text_parts.append(description)
                
            naics_code = self._extract_field_value(general, 'naics_code')
            if naics_code:
                text_parts.append(f"NAICS: {naics_code}")
                
        elif category == 'jobs':
            # For jobs, include description and SOC code
            description = self._extract_field_value(general, 'description')
            if description:
                text_parts.append(description)
                
            soc_code = self._extract_field_value(general, 'soc_code')
            if soc_code:
                text_parts.append(f"SOC: {soc_code}")
                
        else:
            # For other categories, include description and comments
            description = self._extract_field_value(general, 'description')
            if description:
                text_parts.append(description)
                
            comments = self._extract_field_value(general, 'comments')
            if comments:
                text_parts.append(comments)
        
        return ' '.join(text_parts).strip()
        
    def _extract_field_value(self, section: Dict, field_name: str) -> Optional[str]:
        """Extract field value from a section."""
        field = section.get(field_name, {})
        if isinstance(field, dict):
            return field.get('value')
        return field
        
    def preprocess_text(self, text: str) -> List[str]:
        """Preprocess text for vectorization."""
        # Convert to lowercase and remove special characters
        text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text.lower())
        
        # Split into words and filter out short words
        words = [word.strip() for word in text.split() if len(word.strip()) > 2]
        
        # Remove common stop words
        stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 
                     'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 
                     'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 
                     'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those'}
        
        words = [word for word in words if word not in stop_words]
        
        return words

    def build_vocabulary(self, json_dir: Path):
        """Build vocabulary from all text content."""
        if self.vocabulary_built:
            return
            
        logger.info("Building vocabulary from text content...")
        word_counts = Counter()
        
        for category in self.embeddable_categories.keys():
            category_dir = json_dir / category
            if not category_dir.exists():
                continue
                
            for json_file in category_dir.glob("*.json"):
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    text_content = self.extract_text_content(data, category)
                    words = self.preprocess_text(text_content)
                    word_counts.update(words)
                    
                except Exception as e:
                    logger.warning(f"Error processing {json_file} for vocabulary: {e}")
        
        # Keep the top 512 most common words as vocabulary
        # This gives us our embedding dimensions
        most_common = word_counts.most_common(512)
        self.vocabulary = {word: idx for idx, (word, count) in enumerate(most_common)}
        self.vocabulary_built = True
        
        logger.info(f"Built vocabulary with {len(self.vocabulary)} terms")

    def generate_embedding_tfidf(self, text: str) -> List[float]:
        """Generate simple TF-IDF style embedding using built vocabulary."""
        if not self.vocabulary_built:
            logger.error("Vocabulary not built. Call build_vocabulary() first.")
            return [0.0] * 512
            
        words = self.preprocess_text(text)
        word_counts = Counter(words)
        
        # Calculate term frequencies
        total_words = len(words)
        embedding = [0.0] * 512
        
        for word, count in word_counts.items():
            if word in self.vocabulary:
                idx = self.vocabulary[word]
                tf = count / total_words if total_words > 0 else 0
                # Simple frequency-based score (could be enhanced with IDF)
                embedding[idx] = tf
        
        # Normalize the vector
        magnitude = math.sqrt(sum(x**2 for x in embedding))
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]
        
        logger.debug(f"Generated TF-IDF embedding for text: {text[:50]}...")
        return embedding
        
    def create_vector_indices(self):
        """Create vector indices for all embeddable categories."""
        with self.driver.session() as session:
            for category, config in self.vector_configs.items():
                label = self.embeddable_categories[category]
                index_name = config['index_name']
                property_name = config['property']
                dimensions = config['dimensions']
                similarity_function = config['similarity_function']
                
                # Create vector index
                query = f"""
                CREATE VECTOR INDEX `{index_name}` IF NOT EXISTS
                FOR (n:{label}) ON (n.{property_name})
                OPTIONS {{
                    indexConfig: {{
                        `vector.dimensions`: {dimensions},
                        `vector.similarity_function`: '{similarity_function}'
                    }}
                }}
                """
                
                try:
                    session.run(query)
                    logger.info(f"Created vector index: {index_name} for {label} nodes")
                except Exception as e:
                    logger.warning(f"Vector index creation failed for {index_name}: {e}")
                    
    def process_json_files_for_embeddings(self, json_dir: Path) -> Dict[str, int]:
        """Process JSON files and generate embeddings for all entities."""
        # First, build vocabulary from all text content
        self.build_vocabulary(json_dir)
        
        stats = {}
        
        for category in self.embeddable_categories.keys():
            category_dir = json_dir / category
            if not category_dir.exists():
                logger.warning(f"Category directory not found: {category_dir}")
                continue
                
            processed_count = 0
            logger.info(f"Processing embeddings for category: {category}")
            
            for json_file in category_dir.glob("*.json"):
                if self.process_single_file_embedding(json_file, category):
                    processed_count += 1
                    
                if processed_count % 100 == 0:
                    logger.info(f"Processed {processed_count} {category} entities...")
                    
            stats[category] = processed_count
            logger.info(f"Completed {category}: {processed_count} embeddings generated")
            
        return stats
        
    def process_single_file_embedding(self, json_file: Path, category: str) -> bool:
        """Process a single JSON file and add embedding to the corresponding node."""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Extract text content for embedding
            text_content = self.extract_text_content(data, category)
            if not text_content:
                logger.warning(f"No text content found for {json_file}")
                return False
                
            # Generate embedding using TF-IDF approach
            embedding = self.generate_embedding_tfidf(text_content)
                
            if not embedding:
                logger.error(f"Failed to generate embedding for {json_file}")
                return False
                
            # Get UUID from metadata
            uuid = data.get('metadata', {}).get('uuid')
            if not uuid:
                logger.error(f"No UUID found in {json_file}")
                return False
                
            # Update node with embedding
            return self.update_node_embedding(uuid, embedding)
            
        except Exception as e:
            logger.error(f"Error processing {json_file}: {e}")
            return False
            
    def update_node_embedding(self, uuid: str, embedding: List[float]) -> bool:
        """Update a node with its embedding vector."""
        try:
            with self.driver.session() as session:
                # Use the new db.create.setNodeVectorProperty function
                query = """
                MATCH (n {uuid: $uuid})
                CALL db.create.setNodeVectorProperty(n, 'embedding', $embedding)
                RETURN n.uuid as uuid
                """
                
                result = session.run(query, uuid=uuid, embedding=embedding)
                record = result.single()
                
                if record:
                    logger.debug(f"Updated embedding for node: {uuid}")
                    return True
                else:
                    logger.error(f"Node not found for UUID: {uuid}")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to update embedding for {uuid}: {e}")
            return False
            
    def query_similar_entities(self, query_text: str, category: str, limit: int = 10) -> List[Dict]:
        """Query for similar entities using vector search."""
        # Generate embedding for query text
        query_embedding = self.generate_embedding_tfidf(query_text)
            
        if not query_embedding:
            logger.error("Failed to generate embedding for query")
            return []
            
        config = self.vector_configs.get(category)
        if not config:
            logger.error(f"No vector config for category: {category}")
            return []
            
        index_name = config['index_name']
        
        try:
            with self.driver.session() as session:
                query = f"""
                CALL db.index.vector.queryNodes('{index_name}', {limit}, $embedding)
                YIELD node, score
                RETURN node.uuid as uuid, node.name as name, score
                ORDER BY score DESC
                """
                
                result = session.run(query, embedding=query_embedding)
                return [dict(record) for record in result]
                
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
            
    def get_embedding_statistics(self) -> Dict[str, Any]:
        """Get statistics about embeddings in the database."""
        stats = {}
        
        try:
            with self.driver.session() as session:
                for category, label in self.embeddable_categories.items():
                    query = f"""
                    MATCH (n:{label})
                    RETURN 
                        count(n) as total_nodes,
                        count(n.embedding) as nodes_with_embeddings,
                        count(n) - count(n.embedding) as nodes_without_embeddings
                    """
                    
                    result = session.run(query)
                    record = result.single()
                    if record:
                        stats[category] = dict(record)
                        
        except Exception as e:
            logger.error(f"Failed to get embedding statistics: {e}")
            
        return stats


def main():
    """Main function for vector embedding generation."""
    # Get environment variables
    neo4j_uri = os.getenv('NEO4J_CONNECTION_URI')
    neo4j_username = os.getenv('NEO4J_USERNAME')
    neo4j_password = os.getenv('NEO4J_PASSWORD')
    
    if not all([neo4j_uri, neo4j_username, neo4j_password]):
        logger.error("Missing required Neo4j environment variables")
        sys.exit(1)
        
    logger.info("Using Neo4j native text embeddings (TF-IDF based)")
    
    # Set up paths
    json_dir = Path("data/formatted/json")
    if not json_dir.exists():
        logger.error(f"JSON directory not found: {json_dir}")
        sys.exit(1)
        
    # Initialize embedder
    embedder = VectorEmbedder(neo4j_uri, neo4j_username, neo4j_password)
    
    try:
        # Test connection
        if not embedder.test_connection():
            logger.error("Cannot connect to Neo4j database")
            sys.exit(1)
            
        logger.info("Connected to Neo4j successfully")
        
        # Create vector indices
        logger.info("Creating vector indices...")
        embedder.create_vector_indices()
        
        # Process all JSON files to generate embeddings
        logger.info("Generating native text embeddings for all entities...")
        stats = embedder.process_json_files_for_embeddings(json_dir)
        
        logger.info("Embedding generation complete!")
        logger.info("Statistics:")
        for category, count in stats.items():
            logger.info(f"  {category}: {count} embeddings generated")
            
        # Get final statistics
        final_stats = embedder.get_embedding_statistics()
        logger.info("\nFinal embedding statistics:")
        for category, data in final_stats.items():
            logger.info(f"  {category}: {data}")
            
    except Exception as e:
        logger.error(f"Vector embedding process failed: {e}")
        sys.exit(1)
    finally:
        embedder.close()


if __name__ == "__main__":
    main()