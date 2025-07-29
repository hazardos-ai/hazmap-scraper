#!/usr/bin/env python3
"""
Tests for Neo4j migration functionality.
"""

import json
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))
from scripts.neo4j_migration import Neo4jMigrator


class TestNeo4jMigrator:
    """Test suite for Neo4j migration functionality."""
    
    @pytest.fixture
    def sample_json_data(self):
        """Sample JSON data for testing."""
        return {
            "metadata": {
                "scraped_from": "https://haz-map.com/Agents/1",
                "entity_name": "Asbestos",
                "category": "agents",
                "uuid": "test-uuid-123",
                "scraped_at": "2025-07-23T18:20:26.358653"
            },
            "parsed_at": "2025-07-24T01:20:14.142245",
            "sections": {
                "general": {
                    "agent_name": {
                        "value": "Asbestos"
                    },
                    "cas_number": {
                        "value": "1332-21-4"
                    },
                    "formula": {
                        "value": "varies"
                    }
                }
            },
            "cross_references": [
                {
                    "type": "name_match",
                    "text": "lung cancer",
                    "confidence": 1.0,
                    "uuid": "disease-uuid-456",
                    "name": "Lung cancer",
                    "category": "diseases"
                },
                {
                    "type": "name_match",
                    "text": "low confidence match",
                    "confidence": 0.5,
                    "uuid": "other-uuid-789",
                    "name": "Other entity",
                    "category": "other"
                }
            ]
        }
    
    @pytest.fixture
    def mock_driver(self):
        """Mock Neo4j driver."""
        driver = Mock()
        session = Mock()
        
        # Create context manager mock
        context_manager = Mock()
        context_manager.__enter__ = Mock(return_value=session)
        context_manager.__exit__ = Mock(return_value=None)
        driver.session.return_value = context_manager
        
        return driver, session
    
    def test_migrator_initialization(self, mock_driver):
        """Test migrator initialization."""
        driver, session = mock_driver
        
        with patch('neo4j.GraphDatabase.driver', return_value=driver):
            migrator = Neo4jMigrator("bolt://localhost:7687", "neo4j", "password")
            
            assert migrator.driver == driver
            assert "agents" in migrator.category_mappings
            assert migrator.category_mappings["agents"] == "Agent"
    
    def test_connection_test_success(self, mock_driver):
        """Test successful connection test."""
        driver, session = mock_driver
        result = Mock()
        result.single.return_value = {"test": 1}
        session.run.return_value = result
        
        with patch('neo4j.GraphDatabase.driver', return_value=driver):
            migrator = Neo4jMigrator("bolt://localhost:7687", "neo4j", "password")
            assert migrator.test_connection() == True
    
    def test_connection_test_failure(self, mock_driver):
        """Test connection test failure."""
        driver, session = mock_driver
        session.run.side_effect = Exception("Connection failed")
        
        with patch('neo4j.GraphDatabase.driver', return_value=driver):
            migrator = Neo4jMigrator("bolt://localhost:7687", "neo4j", "password")
            assert migrator.test_connection() == False
    
    def test_extract_node_properties_agent(self, sample_json_data):
        """Test node property extraction for agents."""
        with patch('neo4j.GraphDatabase.driver'):
            migrator = Neo4jMigrator("bolt://localhost:7687", "neo4j", "password")
            
            properties = migrator.extract_node_properties(sample_json_data, "agents")
            
            assert properties["uuid"] == "test-uuid-123"
            assert properties["name"] == "Asbestos"
            assert properties["cas_number"] == "1332-21-4"
            assert properties["formula"] == "varies"
            assert properties["source_url"] == "https://haz-map.com/Agents/1"
    
    def test_extract_relationships_confidence_filtering(self, sample_json_data):
        """Test that only confidence 1.0 relationships are extracted."""
        with patch('neo4j.GraphDatabase.driver'):
            migrator = Neo4jMigrator("bolt://localhost:7687", "neo4j", "password")
            
            relationships = migrator.extract_relationships(sample_json_data)
            
            # Should only have one relationship (confidence 1.0)
            assert len(relationships) == 1
            
            source_uuid, target_uuid, rel_type, rel_props = relationships[0]
            assert source_uuid == "test-uuid-123"
            assert target_uuid == "disease-uuid-456"
            assert rel_type == "CAUSES"
            assert rel_props["confidence"] == 1.0
    
    def test_determine_relationship_type(self):
        """Test relationship type determination."""
        with patch('neo4j.GraphDatabase.driver'):
            migrator = Neo4jMigrator("bolt://localhost:7687", "neo4j", "password")
            
            # Test known mappings
            assert migrator._determine_relationship_type("agents", "diseases") == "CAUSES"
            assert migrator._determine_relationship_type("diseases", "findings") == "MANIFESTS_AS"
            assert migrator._determine_relationship_type("jobs", "agents") == "EXPOSED_TO"
            
            # Test same-category relationship
            assert migrator._determine_relationship_type("agents", "agents") == "SIMILAR_TO"
            
            # Test unknown mapping
            assert migrator._determine_relationship_type("unknown", "other") is None
    
    def test_create_node_success(self, mock_driver):
        """Test successful node creation."""
        driver, session = mock_driver
        session.run.return_value = None
        
        with patch('neo4j.GraphDatabase.driver', return_value=driver):
            migrator = Neo4jMigrator("bolt://localhost:7687", "neo4j", "password")
            
            properties = {
                "uuid": "test-123",
                "name": "Test Entity",
                "cas_number": "1234-56-7"
            }
            
            result = migrator.create_node(session, "agents", properties)
            assert result == True
            session.run.assert_called_once()
    
    def test_create_node_failure(self, mock_driver):
        """Test node creation failure."""
        driver, session = mock_driver
        session.run.side_effect = Exception("Query failed")
        
        with patch('neo4j.GraphDatabase.driver', return_value=driver):
            migrator = Neo4jMigrator("bolt://localhost:7687", "neo4j", "password")
            
            properties = {"uuid": "test-123", "name": "Test Entity"}
            result = migrator.create_node(session, "agents", properties)
            assert result == False
    
    def test_create_relationship_success(self, mock_driver):
        """Test successful relationship creation."""
        driver, session = mock_driver
        session.run.return_value = None
        
        with patch('neo4j.GraphDatabase.driver', return_value=driver):
            migrator = Neo4jMigrator("bolt://localhost:7687", "neo4j", "password")
            
            rel_props = {
                "confidence": 1.0,
                "reference_type": "name_match",
                "source_text": "test text"
            }
            
            result = migrator.create_relationship(
                session, "uuid1", "uuid2", "CAUSES", rel_props
            )
            assert result == True
            session.run.assert_called_once()
    
    def test_load_json_file(self, sample_json_data):
        """Test JSON file loading."""
        with patch('neo4j.GraphDatabase.driver'):
            migrator = Neo4jMigrator("bolt://localhost:7687", "neo4j", "password")
            
            # Create temporary JSON file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(sample_json_data, f)
                temp_file = Path(f.name)
            
            try:
                data = migrator.load_json_file(temp_file)
                assert data == sample_json_data
            finally:
                temp_file.unlink()
    
    def test_extract_field_value(self):
        """Test field value extraction."""
        with patch('neo4j.GraphDatabase.driver'):
            migrator = Neo4jMigrator("bolt://localhost:7687", "neo4j", "password")
            
            # Test dict field
            section = {"field1": {"value": "test_value"}}
            assert migrator._extract_field_value(section, "field1") == "test_value"
            
            # Test direct field
            section = {"field2": "direct_value"}
            assert migrator._extract_field_value(section, "field2") == "direct_value"
            
            # Test missing field
            assert migrator._extract_field_value(section, "missing") is None
    
    def test_extract_boolean_field(self):
        """Test boolean field extraction."""
        with patch('neo4j.GraphDatabase.driver'):
            migrator = Neo4jMigrator("bolt://localhost:7687", "neo4j", "password")
            
            # Test various boolean representations
            section = {
                "bool_true": {"value": True},
                "bool_false": {"value": False},
                "str_true": {"value": "true"},
                "str_yes": {"value": "yes"},
                "str_false": {"value": "false"},
                "missing": None
            }
            
            assert migrator._extract_boolean_field(section, "bool_true") == True
            assert migrator._extract_boolean_field(section, "bool_false") == False
            assert migrator._extract_boolean_field(section, "str_true") == True
            assert migrator._extract_boolean_field(section, "str_yes") == True
            assert migrator._extract_boolean_field(section, "str_false") == False
            assert migrator._extract_boolean_field(section, "missing") is None
    
    def test_migrate_file_success(self, sample_json_data, mock_driver):
        """Test successful file migration."""
        driver, session = mock_driver
        session.run.return_value = None
        
        with patch('neo4j.GraphDatabase.driver', return_value=driver):
            migrator = Neo4jMigrator("bolt://localhost:7687", "neo4j", "password")
            
            # Create temporary JSON file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(sample_json_data, f)
                temp_file = Path(f.name)
            
            try:
                result = migrator.migrate_file(temp_file)
                assert result == True
                session.run.assert_called_once()
            finally:
                temp_file.unlink()


def test_schema_compliance():
    """Test that the migration follows the graph schema."""
    with patch('neo4j.GraphDatabase.driver'):
        migrator = Neo4jMigrator("bolt://localhost:7687", "neo4j", "password")
        
        # Test all category mappings exist
        expected_categories = [
            'agents', 'diseases', 'processes', 'industries',
            'job_tasks', 'jobs', 'findings', 'activities'
        ]
        
        for category in expected_categories:
            assert category in migrator.category_mappings
        
        # Test all relationship types are defined
        test_cases = [
            ('agents', 'diseases', 'CAUSES'),
            ('diseases', 'findings', 'MANIFESTS_AS'),
            ('jobs', 'agents', 'EXPOSED_TO'),
            ('job_tasks', 'agents', 'EXPOSED_TO'),
            ('jobs', 'job_tasks', 'INVOLVES_TASK'),
            ('jobs', 'industries', 'OPERATES_IN'),
            ('industries', 'processes', 'INVOLVES_PROCESS'),
            ('processes', 'agents', 'USES_AGENT'),
            ('activities', 'agents', 'INVOLVES_ACTIVITY'),
            ('agents', 'agents', 'SIMILAR_TO'),
        ]
        
        for source, target, expected_rel in test_cases:
            actual_rel = migrator._determine_relationship_type(source, target)
            assert actual_rel == expected_rel, f"Expected {expected_rel} for {source}->{target}, got {actual_rel}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])