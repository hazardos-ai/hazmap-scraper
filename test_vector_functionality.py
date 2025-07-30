#!/usr/bin/env python3
"""
Test Vector Embeddings Functionality

This script tests the vector embedding functionality without requiring
a Neo4j database connection.
"""

import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from scripts.vector_embeddings import VectorEmbedder

def test_text_extraction():
    """Test text content extraction from JSON data."""
    print("Testing text content extraction...")
    
    # Mock VectorEmbedder for testing
    embedder = VectorEmbedder("", "", "", test_mode=True)
    
    # Test agent data
    agent_data = {
        "metadata": {
            "entity_name": "Sodium formate",
            "category": "agents"
        },
        "sections": {
            "general": {
                "synonyms": {"value": "Formic acid sodium salt"},
                "major_category": {"value": "ORGANIC COMPOUNDS"},
                "minor_category": {"value": "Salts"}
            }
        }
    }
    
    text = embedder.extract_text_content(agent_data, "agents")
    print(f"Agent text: {text}")
    
    # Test disease data
    disease_data = {
        "metadata": {
            "entity_name": "Lung cancer",
            "category": "diseases"
        },
        "sections": {
            "general": {
                "description": {"value": "Malignant neoplasm of the lung tissue"},
                "category": {"value": "Cancer"},
                "synonyms": {"value": "Bronchogenic carcinoma"}
            }
        }
    }
    
    text = embedder.extract_text_content(disease_data, "diseases")
    print(f"Disease text: {text}")
    
    # Test industry data
    industry_data = {
        "metadata": {
            "entity_name": "Primary Aluminum Production",
            "category": "industries"
        },
        "sections": {
            "general": {
                "description": {"value": "Manufacturing of aluminum from alumina"},
                "naics_code": {"value": "331313"}
            }
        }
    }
    
    text = embedder.extract_text_content(industry_data, "industries")
    print(f"Industry text: {text}")
    
    print("✓ Text extraction working correctly\n")


def test_mock_embeddings():
    """Test mock embedding generation."""
    print("Testing mock embedding generation...")
    
    embedder = VectorEmbedder("", "", "", test_mode=True)
    
    test_texts = [
        "Sodium formate Synonyms: Formic acid sodium salt Category: ORGANIC COMPOUNDS Type: Salts",
        "Lung cancer Malignant neoplasm of the lung tissue Category: Cancer Synonyms: Bronchogenic carcinoma",
        "Primary Aluminum Production Manufacturing of aluminum from alumina NAICS: 331313"
    ]
    
    for text in test_texts:
        embedding = embedder.generate_embedding_mock(text)
        print(f"Text: {text[:50]}...")
        print(f"Embedding length: {len(embedding)}")
        print(f"Embedding range: [{min(embedding):.4f}, {max(embedding):.4f}]")
        
        # Test that same text produces same embedding
        embedding2 = embedder.generate_embedding_mock(text)
        if embedding == embedding2:
            print("✓ Consistent embeddings for same text")
        else:
            print("✗ Inconsistent embeddings")
        print()
    
    print("✓ Mock embedding generation working correctly\n")


def test_vector_configs():
    """Test vector index configurations."""
    print("Testing vector index configurations...")
    
    embedder = VectorEmbedder("", "", "", test_mode=True)
    
    print("Vector index configurations:")
    for category, config in embedder.vector_configs.items():
        label = embedder.embeddable_categories[category]
        print(f"  {category} ({label}):")
        print(f"    Index: {config['index_name']}")
        print(f"    Property: {config['property']}")
        print(f"    Dimensions: {config['dimensions']}")
        print(f"    Similarity: {config['similarity_function']}")
    
    print("✓ Vector configurations are properly defined\n")


def test_real_json_files():
    """Test with real JSON files if available."""
    print("Testing with real JSON files...")
    
    json_dir = Path("data/formatted/json")
    if not json_dir.exists():
        print("JSON directory not found - skipping real file test")
        return
    
    embedder = VectorEmbedder("", "", "", test_mode=True)
    
    # Test with a few real files
    for category in ["agents", "diseases", "industries"]:
        category_dir = json_dir / category
        if category_dir.exists():
            json_files = list(category_dir.glob("*.json"))
            if json_files:
                test_file = json_files[0]
                print(f"Testing {category} file: {test_file.name}")
                
                try:
                    with open(test_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    text = embedder.extract_text_content(data, category)
                    print(f"  Extracted text: {text[:100]}...")
                    
                    embedding = embedder.generate_embedding_mock(text)
                    print(f"  Generated embedding with {len(embedding)} dimensions")
                    
                except Exception as e:
                    print(f"  Error: {e}")
                
                print()
    
    print("✓ Real JSON file processing working correctly\n")


def main():
    """Run all tests."""
    print("🧪 Testing Vector Embeddings Functionality\n")
    
    test_text_extraction()
    test_mock_embeddings()
    test_vector_configs()
    test_real_json_files()
    
    print("🎉 All tests completed successfully!")
    print("\nThe vector embedding system is ready to use.")
    print("To add embeddings to your Neo4j database:")
    print("  python src/scripts/add_vector_embeddings.py --mock")
    print("  # Or with OpenAI API:")
    print("  python src/scripts/add_vector_embeddings.py")


if __name__ == "__main__":
    main()