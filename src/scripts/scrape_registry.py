#!/usr/bin/env python3
"""
Script to scrape entity names from haz-map.com and generate a UUID registry.

This script:
1. Loads the sitemap.yml configuration
2. Scrapes each URL to extract entity names
3. Generates unique UUIDs for each entity
4. Creates a comprehensive registry in YAML format
5. Saves the registry for use in building Neo4j knowledge graph
"""

import asyncio
import re
import sys
import time
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
from uuid import uuid4
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pydantic import ValidationError

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.registry import EntityRegistry, CategoryRegistry, EntityEntry


class HazMapScraper:
    """Scraper for haz-map.com entity data."""

    def __init__(
        self, sitemap_path: str = "src/models/sitemap.yml", delay: float = 1.0
    ):
        """Initialize the scraper."""
        self.sitemap_path = Path(sitemap_path)
        self.delay = delay  # Delay between requests to be respectful
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (compatible; HazMapScraper/1.0; +https://github.com/hazardos-ai/hazmap-scraper)"
            }
        )
        self.used_uuids: Set[str] = set()

    def load_sitemap(self) -> Dict:
        """Load the sitemap configuration."""
        with open(self.sitemap_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    def generate_unique_uuid(self) -> str:
        """Generate a unique UUID that hasn't been used."""
        while True:
            new_uuid = str(uuid4())
            if new_uuid not in self.used_uuids:
                self.used_uuids.add(new_uuid)
                return new_uuid

    def is_valid_entity_name(self, name: str) -> bool:
        """Check if the extracted name is valid (not a placeholder)."""
        if not name:
            return False

        # Skip entries that are just "| Haz-Map" or similar placeholders
        invalid_names = [
            "| Haz-Map",
            "| HazMap",
            "Haz-Map",
            "HazMap",
            "page not found",
            "error",
            "404",
        ]

        return name.lower() not in [invalid.lower() for invalid in invalid_names]

    def extract_entity_name(self, html_content: str, url: str) -> Optional[str]:
        """Extract the entity name from HTML content."""
        soup = BeautifulSoup(html_content, "html.parser")

        # Try different selectors to find the entity name
        name_selectors = [
            "h1",  # Main heading
            "title",  # Page title
            ".page-title",  # Common class name
            "#title",  # Common ID
            "h2",  # Secondary heading
            ".entity-name",  # Specific class if it exists
        ]

        for selector in name_selectors:
            element = soup.select_one(selector)
            if element:
                name = element.get_text(strip=True)
                if self.is_valid_entity_name(name):
                    # Clean up the name
                    name = re.sub(r"\\s+", " ", name)  # Normalize whitespace
                    name = name.strip()
                    if name:
                        return name

        # If no name found, try meta tags
        meta_title = soup.find("meta", {"property": "og:title"})
        if meta_title and meta_title.get("content"):
            name = meta_title.get("content").strip()
            if self.is_valid_entity_name(name):
                return name

        return None

    def scrape_entity(self, url: str, category: str) -> Optional[EntityEntry]:
        """Scrape a single entity."""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            name = self.extract_entity_name(response.text, url)
            if not name:
                print(f"  ⚠️  Skipping invalid entry: {url}")
                return None

            entity = EntityEntry(uuid=self.generate_unique_uuid(), name=name, url=url)

            print(f"  ✅ {name}")
            return entity

        except requests.exceptions.RequestException as e:
            print(f"  ❌ Error scraping {url}: {e}")
            return None
        except ValidationError as e:
            print(f"  ❌ Validation error for {url}: {e}")
            return None

    def check_existing_registry(self, category_key: str) -> bool:
        """Check if a registry file already exists for the category."""
        data_dir = Path("data")
        if not data_dir.exists():
            return False

        # Look for existing registry files for this category
        pattern = f"{category_key}_registry_*.yml"
        existing_files = list(data_dir.glob(pattern))

        if existing_files:
            latest_file = max(existing_files, key=lambda f: f.stat().st_mtime)
            print(f"  📁 Found existing registry: {latest_file.name}")
            return True

        return False

    def save_category_registry(
        self, category_key: str, category_registry: CategoryRegistry
    ) -> str:
        """Save a category registry to a timestamped YAML file."""
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)

        # Create timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{category_key}_registry_{timestamp}.yml"
        file_path = data_dir / filename

        # Convert to dictionary for YAML serialization
        registry_dict = {
            "category": category_key,
            "category_name": category_registry.category_name,
            "category_description": category_registry.category_description,
            "root_url": str(category_registry.root_url),
            "total_expected": category_registry.total_expected,
            "total_scraped": category_registry.total_scraped,
            "scraped_at": datetime.now().isoformat(),
            "entities": [
                {
                    "uuid": str(entity.uuid),
                    "name": entity.name,
                    "url": str(entity.url),
                    "category": entity.category,
                }
                for entity in category_registry.entities
            ],
        }

        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(
                registry_dict,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )

        print(f"  💾 Saved registry to: {filename}")
        return str(file_path)

    def scrape_category(
        self, category_key: str, category_config: Dict
    ) -> Optional[CategoryRegistry]:
        """Scrape all entities in a category."""
        print(f"\\n🔍 Scraping category: {category_config['name']}")

        # Check if registry already exists
        if self.check_existing_registry(category_key):
            print(f"  ⏭️  Skipping {category_key} - registry already exists")
            return None

        print(f"  📊 Expected entities: {category_config['total']}")

        category_registry = CategoryRegistry(
            category_name=category_config["name"],
            category_description=category_config["name"],
            root_url=category_config["root_url"],
            total_expected=category_config["total"],
        )

        root_url = category_config["root_url"]
        total = category_config["total"]

        # Progress tracking
        scraped_count = 0
        skipped_count = 0

        for i in range(1, total + 1):
            url = f"{root_url}{i}"

            # Print progress every 100 entries or at key milestones
            if i % 100 == 0 or i == 1 or i == total:
                percentage = (i / total) * 100
                print(f"  📈 Progress: {i}/{total} ({percentage:.1f}%)")

            entity = self.scrape_entity(url, category_key)

            if entity:
                category_registry.entities.append(entity)
                scraped_count += 1
            else:
                skipped_count += 1

            # Be respectful with delays
            if i < total:  # Don't delay after the last request
                time.sleep(self.delay)

        print(f"  ✅ Completed: {scraped_count} scraped, {skipped_count} skipped")

        # Save the registry
        self.save_category_registry(category_key, category_registry)

        return category_registry

    def scrape_all(self) -> List[str]:
        """Scrape all entities from all categories."""
        print("🚀 Starting HazMap entity scraping...")
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        sitemap = self.load_sitemap()
        created_files = []

        for category_key, category_config in sitemap.items():
            try:
                category_registry = self.scrape_category(category_key, category_config)
                if category_registry:
                    # File was already saved in scrape_category
                    pass
            except Exception as e:
                print(f"❌ Error scraping category {category_key}: {e}")
                continue

        print(f"\\n🎉 Scraping complete!")
        print(f"⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return created_files


def main():
    """Main function to run the scraper."""
    scraper = HazMapScraper(delay=1.0)  # 1 second delay between requests

    try:
        created_files = scraper.scrape_all()
        print("\\n✅ Scraping completed successfully!")
        return created_files
    except KeyboardInterrupt:
        print("\\n⏹️  Scraping interrupted by user")
    except Exception as e:
        print(f"\\n❌ Scraping failed: {e}")
        raise


if __name__ == "__main__":
    main()
