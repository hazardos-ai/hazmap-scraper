#!/usr/bin/env python3
"""
Test script to verify the scraper works on a small sample.
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import yaml
    import pytest
    from scripts.scrape_registry import HazMapScraper
except ImportError as e:
    print(f"Missing dependencies: {e}")
    print("Please install with: pixi install")
    sys.exit(1)


class TestHazMapScraper:
    """Test suite for HazMapScraper"""

    def test_scraper_initialization(self):
        """Test that scraper initializes correctly"""
        # Create a test sitemap
        test_sitemap = {
            "findings": {
                "name": "Symptoms/Findings",
                "root_url": "https://haz-map.com/Findings/",
                "total": 3,
            }
        }

        test_sitemap_path = Path("test_sitemap.yml")
        with open(test_sitemap_path, "w") as f:
            yaml.dump(test_sitemap, f)

        try:
            scraper = HazMapScraper(sitemap_path=str(test_sitemap_path), delay=0.1)
            assert scraper.sitemap == test_sitemap
            assert scraper.delay == 0.1
        finally:
            if test_sitemap_path.exists():
                test_sitemap_path.unlink()

    def test_is_valid_entity_name(self):
        """Test entity name validation"""
        scraper = HazMapScraper()

        # Valid names
        assert scraper.is_valid_entity_name("Asbestos") == True
        assert scraper.is_valid_entity_name("dyspnea, exertional") == True
        assert scraper.is_valid_entity_name("weight loss") == True

        # Invalid names
        assert scraper.is_valid_entity_name("| Haz-Map") == False
        assert scraper.is_valid_entity_name("| Haz-Map ") == False
        assert scraper.is_valid_entity_name(" | Haz-Map") == False
        assert scraper.is_valid_entity_name("") == False
        assert scraper.is_valid_entity_name(None) == False

    @patch("requests.get")
    def test_scrape_entity_success(self, mock_get):
        """Test successful entity scraping"""
        # Mock HTML response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <body>
                <div class="container">
                    <h1>Asbestos</h1>
                </div>
            </body>
        </html>
        """
        mock_get.return_value = mock_response

        scraper = HazMapScraper()
        entity = scraper.scrape_entity("https://haz-map.com/Agents/1", "agents")

        assert entity is not None
        assert entity.name == "Asbestos"
        assert entity.url == "https://haz-map.com/Agents/1"
        assert len(entity.uuid) == 36  # UUID length

    @patch("requests.get")
    def test_scrape_entity_invalid_name(self, mock_get):
        """Test entity scraping with invalid name"""
        # Mock HTML response with invalid name
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <body>
                <div class="container">
                    <h1>| Haz-Map</h1>
                </div>
            </body>
        </html>
        """
        mock_get.return_value = mock_response

        scraper = HazMapScraper()
        entity = scraper.scrape_entity("https://haz-map.com/Agents/1", "agents")

        assert entity is None

    @patch("requests.get")
    def test_scrape_entity_http_error(self, mock_get):
        """Test entity scraping with HTTP error"""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        scraper = HazMapScraper()
        entity = scraper.scrape_entity("https://haz-map.com/Agents/999", "agents")

        assert entity is None

    def test_check_existing_registry(self):
        """Test checking for existing registry files"""
        scraper = HazMapScraper()

        # Test with non-existent file
        assert scraper.check_existing_registry("nonexistent") == False

        # Test with existing file
        test_file = Path("data/test_registry_20250716_000000.yml")
        test_file.parent.mkdir(exist_ok=True)
        test_file.write_text("test")

        try:
            assert scraper.check_existing_registry("test") == True
        finally:
            if test_file.exists():
                test_file.unlink()


def test_manual_scraper():
    """Manual test function for interactive testing"""
    print("🧪 Testing HazMap scraper...")

    # Create a test sitemap with just a few entries
    test_sitemap = {
        "findings": {
            "name": "Symptoms/Findings",
            "root_url": "https://haz-map.com/Findings/",
            "total": 3,  # Test with just 3 entries
        }
    }

    # Save test sitemap
    test_sitemap_path = Path("test_sitemap.yml")
    with open(test_sitemap_path, "w") as f:
        yaml.dump(test_sitemap, f)

    try:
        # Test the scraper
        scraper = HazMapScraper(sitemap_path=str(test_sitemap_path), delay=0.5)

        # Test individual URL scraping
        print("\\n1. Testing individual URL scraping...")
        test_url = "https://haz-map.com/Findings/1"
        entity = scraper.scrape_entity(test_url, "findings")

        if entity:
            print(f"✅ Successfully scraped: {entity.name}")
            print(f"   UUID: {entity.uuid}")
            print(f"   URL: {entity.url}")
        else:
            print("❌ Failed to scrape individual entity")
            return False

        # Test category scraping
        print("\\n2. Testing category scraping...")
        category_config = test_sitemap["findings"]
        category_registry = scraper.scrape_category("findings", category_config)

        print(f"✅ Category scraping completed")
        print(f"   Scraped: {len(category_registry.entities)} entities")
        print(f"   Expected: {category_config['total']} entities")

        # Show scraped entities
        for i, entity in enumerate(category_registry.entities, 1):
            print(f"   {i}. {entity.name} ({entity.uuid})")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        # Clean up
        if test_sitemap_path.exists():
            test_sitemap_path.unlink()


if __name__ == "__main__":
    success = test_manual_scraper()
    sys.exit(0 if success else 1)
