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
                if name and name.lower() not in ["page not found", "error", "404"]:
                    # Clean up the name
                    name = re.sub(r"\\s+", " ", name)  # Normalize whitespace
                    name = name.strip()
                    if name:
                        return name

        # If no name found, try meta tags
        meta_title = soup.find("meta", {"property": "og:title"})
        if meta_title and meta_title.get("content"):
            return meta_title.get("content").strip()

        # Last resort: extract from URL
        url_parts = url.rstrip("/").split("/")
        if url_parts:
            potential_name = url_parts[-1]
            if potential_name.isdigit():
                return f"Entity {potential_name}"

        return None

    def scrape_entity(self, url: str, category: str) -> Optional[EntityEntry]:
        """Scrape a single entity."""
        try:
            print(f"Scraping: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            name = self.extract_entity_name(response.text, url)
            if not name:
                print(f"  ⚠️  Could not extract name from {url}")
                return None

            entity = EntityEntry(
                uuid=self.generate_unique_uuid(), name=name, url=url, category=category
            )

            print(f"  ✅ {name}")
            return entity

        except requests.exceptions.RequestException as e:
            print(f"  ❌ Error scraping {url}: {e}")
            return None
        except ValidationError as e:
            print(f"  ❌ Validation error for {url}: {e}")
            return None

    def scrape_category(
        self, category_key: str, category_config: Dict
    ) -> CategoryRegistry:
        """Scrape all entities in a category."""
        print(f"\\n🔍 Scraping category: {category_config['name']}")
        print(f"Expected entities: {category_config['total']}")

        category_registry = CategoryRegistry(
            category_name=category_config["name"],
            category_description=category_config["name"],
            root_url=category_config["root_url"],
            total_expected=category_config["total"],
        )

        root_url = category_config["root_url"]
        total = category_config["total"]

        for i in range(1, total + 1):
            url = f"{root_url}{i}"
            entity = self.scrape_entity(url, category_key)

            if entity:
                category_registry.entities.append(entity)

            # Be respectful with delays
            if i < total:  # Don't delay after the last request
                time.sleep(self.delay)

        print(f"✅ Scraped {len(category_registry.entities)} / {total} entities")
        return category_registry

    def scrape_all(
        self, output_path: str = "data/entity_registry.yml"
    ) -> EntityRegistry:
        """Scrape all entities from all categories."""
        print("🚀 Starting HazMap entity scraping...")

        sitemap = self.load_sitemap()
        registry = EntityRegistry()

        for category_key, category_config in sitemap.items():
            try:
                category_registry = self.scrape_category(category_key, category_config)
                registry.categories[category_key] = category_registry
            except Exception as e:
                print(f"❌ Error scraping category {category_key}: {e}")
                continue

        # Save the registry
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        registry.save_to_yaml(str(output_path))

        print(f"\\n🎉 Scraping complete!")
        print(f"Total entities scraped: {registry.total_entities}")
        print(f"Registry saved to: {output_path}")

        # Print summary
        print("\\n📊 Summary by category:")
        for category_key, category in registry.categories.items():
            print(
                f"  {category_key}: {category.total_scraped} / {category.total_expected}"
            )

        return registry


def main():
    """Main function to run the scraper."""
    scraper = HazMapScraper(delay=1.0)  # 1 second delay between requests

    try:
        registry = scraper.scrape_all()
        print("\\n✅ Scraping completed successfully!")
        return registry
    except KeyboardInterrupt:
        print("\\n⏹️  Scraping interrupted by user")
    except Exception as e:
        print(f"\\n❌ Scraping failed: {e}")
        raise


if __name__ == "__main__":
    main()
