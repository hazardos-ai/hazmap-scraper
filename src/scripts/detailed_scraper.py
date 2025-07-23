#!/usr/bin/env python3
"""
Comprehensive scraper for haz-map.com that extracts detailed information
from each entity page and saves it to individual text files.

This script:
1. Loads existing registry files to get entity URLs
2. Scrapes each URL to extract ALL detailed information
3. Saves raw scraped content to individual txt files
4. Organizes files by category (agents, diseases, etc.)
"""

import asyncio
import re
import sys
import time
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from urllib.parse import urljoin, urlparse
import json

import requests
from bs4 import BeautifulSoup, NavigableString

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))


class DetailedHazMapScraper:
    """Detailed scraper for haz-map.com entity data."""

    def __init__(self, delay: Optional[float] = 1.0):
        """Initialize the scraper.

        Args:
            delay: Delay between requests in seconds to be respectful
        """
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (compatible; HazMapDetailedScraper/1.0; +https://github.com/hazardos-ai/hazmap-scraper)"
            }
        )

        # Create data directories
        self.data_root = Path("data")
        self.create_directories()

    def create_directories(self):
        """Create necessary directories for storing scraped data."""
        categories = [
            "agents",
            "diseases",
            "processes",
            "activities",
            "findings",
            "industries",
            "job_tasks",
            "jobs",
        ]

        for category in categories:
            category_dir = self.data_root / category
            category_dir.mkdir(parents=True, exist_ok=True)
            print(f"📁 Created directory: {category_dir}")

    def load_registry_file(self, registry_path: Path) -> Dict[str, Any]:
        """Load a registry file and return the parsed data."""
        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"❌ Error loading registry {registry_path}: {e}")
            return {}

    def find_latest_registry_files(self) -> Dict[str, Path]:
        """Find the latest registry file for each category."""
        registry_files = {}

        # Look for registry files in the registry directory
        registry_dir = self.data_root / "registry"
        if not registry_dir.exists():
            return {}

        for pattern in ["*_registry_*.yml"]:
            for registry_file in registry_dir.glob(pattern):
                # Extract category from filename
                category = registry_file.name.split("_registry_")[0]

                # Keep only the latest file for each category
                if category not in registry_files:
                    registry_files[category] = registry_file
                else:
                    # Compare modification times to get latest
                    if (
                        registry_file.stat().st_mtime
                        > registry_files[category].stat().st_mtime
                    ):
                        registry_files[category] = registry_file

        return registry_files

    def extract_text_content(self, element) -> str:
        """Extract clean text content from a BeautifulSoup element."""
        if not element:
            return ""

        # Get text and clean it up
        text = element.get_text(separator=" ", strip=True)

        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)

        return text.strip()

    def extract_links_from_element(self, element) -> List[Dict[str, str]]:
        """Extract all links from an element with their text and URLs."""
        if not element:
            return []

        links = []
        for link in element.find_all("a", href=True):
            link_text = self.extract_text_content(link)
            href = link.get("href")

            # Convert relative URLs to absolute
            if href.startswith("/"):
                href = f"https://haz-map.com{href}"

            if link_text and href:
                links.append({"text": link_text, "url": href})

        return links

    def extract_detailed_content(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract all detailed content from a page with flexible parsing."""
        data = {
            "url": url,
            "scraped_at": datetime.now().isoformat(),
            "title": "",
            "sections": {},
            "all_links": [],
            "clean_content": "",
        }

        # Extract title
        title_elem = soup.find("h1")
        if title_elem:
            data["title"] = self.extract_text_content(title_elem)

        # Find the main content container
        content_container = soup.find("div", class_="item-details-container")
        if not content_container:
            print(f"⚠️  No content container found for {url}")
            return data

        # Extract all text content without HTML tags for clean processing
        clean_text_lines = []
        current_section = "general"

        # Extract all rows of data flexibly
        rows = content_container.find_all("div", class_="row")

        for row in rows:
            # Check if this is a section header
            if "item-details-subheader" in row.get("class", []):
                section_header = self.extract_text_content(row)
                if section_header:
                    current_section = section_header.lower().strip()
                    # Clean section name for use as dict key
                    current_section = re.sub(r"[^\w\s]", "", current_section)
                    current_section = re.sub(r"\s+", "_", current_section)
                    clean_text_lines.append(f"\n=== {section_header} ===")
                continue

            # Initialize section if not exists
            if current_section not in data["sections"]:
                data["sections"][current_section] = {}

            # Extract all columns
            cols = row.find_all("div", class_=re.compile(r"col-"))

            if len(cols) >= 2:
                # Standard field-value pair
                field_name = self.extract_text_content(cols[0])
                field_value = self.extract_text_content(cols[1])

                # Extract links from the value column
                field_links = self.extract_links_from_element(cols[1])

                if field_name and field_value:
                    # Clean up field name for consistent keys
                    clean_field_name = re.sub(r"[^\w\s]", "", field_name)
                    clean_field_name = (
                        re.sub(r"\s+", "_", clean_field_name).lower().strip("_")
                    )

                    field_data = {
                        "original_name": field_name,
                        "value": field_value,
                        "links": field_links,
                    }

                    data["sections"][current_section][clean_field_name] = field_data

                    # Add to clean text
                    clean_text_lines.append(f"{field_name}: {field_value}")
                    for link in field_links:
                        clean_text_lines.append(f"  -> {link['text']}: {link['url']}")

            elif len(cols) == 1:
                # Single column - might be a list or special content
                content = self.extract_text_content(cols[0])
                links = self.extract_links_from_element(cols[0])

                if content:
                    # Use the section name as the key if no specific field name
                    field_data = {
                        "original_name": current_section.replace("_", " ").title(),
                        "value": content,
                        "links": links,
                    }

                    data["sections"][current_section][
                        f"content_{len(data['sections'][current_section])}"
                    ] = field_data
                    clean_text_lines.append(content)
                    for link in links:
                        clean_text_lines.append(f"  -> {link['text']}: {link['url']}")

        # Handle special nested structures (subrows)
        subrows = content_container.find_all("div", class_="item-details-subrow")
        for subrow in subrows:
            nested_rows = subrow.find_all("div", class_="row")
            for nested_row in nested_rows:
                cols = nested_row.find_all("div", class_=re.compile(r"col-"))
                if len(cols) >= 2:
                    field_name = self.extract_text_content(cols[0])
                    field_value = self.extract_text_content(cols[1])
                    field_links = self.extract_links_from_element(cols[1])

                    if field_name and field_value:
                        clean_field_name = re.sub(r"[^\w\s]", "", field_name)
                        clean_field_name = (
                            re.sub(r"\s+", "_", clean_field_name).lower().strip("_")
                        )

                        field_data = {
                            "original_name": field_name,
                            "value": field_value,
                            "links": field_links,
                        }

                        if "general" not in data["sections"]:
                            data["sections"]["general"] = {}

                        data["sections"]["general"][clean_field_name] = field_data
                        clean_text_lines.append(f"{field_name}: {field_value}")
                        for link in field_links:
                            clean_text_lines.append(
                                f"  -> {link['text']}: {link['url']}"
                            )

        # Extract all links from the page
        data["all_links"] = self.extract_links_from_element(content_container)

        # Store clean text content
        data["clean_content"] = "\n".join(clean_text_lines)

        return data

    def scrape_entity_details(
        self, entity_url: str, entity_name: str, category: str
    ) -> Optional[Dict[str, Any]]:
        """Scrape detailed information from a single entity page."""
        try:
            print(f"  🔍 Scraping: {entity_name}")

            response = self.session.get(entity_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Extract detailed content
            detailed_data = self.extract_detailed_content(soup, entity_url)
            detailed_data["entity_name"] = entity_name
            detailed_data["category"] = category

            return detailed_data

        except requests.exceptions.RequestException as e:
            print(f"  ❌ Network error scraping {entity_url}: {e}")
            return None
        except Exception as e:
            print(f"  ❌ Error scraping {entity_url}: {e}")
            return None

    def save_entity_data(
        self,
        entity_data: Dict[str, Any],
        category: str,
        entity_uuid: str,
        entity_name: str,
    ):
        """Save entity data to a text file with clean formatting."""
        # Create safe filename
        safe_name = re.sub(r"[^\w\s-]", "", entity_name)
        safe_name = re.sub(r"[-\s]+", "-", safe_name)
        safe_name = safe_name.strip("-")[:100]  # Limit length

        filename = f"{entity_uuid}_{safe_name}.txt"
        file_path = self.data_root / category / filename

        # Format the data for human readability
        content_lines = [
            f"Entity: {entity_data.get('entity_name', 'Unknown')}",
            f"Category: {entity_data.get('category', 'Unknown')}",
            f"URL: {entity_data.get('url', '')}",
            f"UUID: {entity_uuid}",
            f"Scraped At: {entity_data.get('scraped_at', '')}",
            "=" * 80,
            "",
        ]

        # Add clean content first (human readable)
        if entity_data.get("clean_content"):
            content_lines.append("CLEAN CONTENT:")
            content_lines.append("-" * 40)
            content_lines.append(entity_data["clean_content"])
            content_lines.append("")

        # Add structured sections
        if entity_data.get("sections"):
            content_lines.append("STRUCTURED DATA:")
            content_lines.append("-" * 40)

            for section_name, section_data in entity_data["sections"].items():
                section_title = section_name.replace("_", " ").title()
                content_lines.append(f"\n[{section_title}]")

                for field_key, field_data in section_data.items():
                    original_name = field_data.get(
                        "original_name", field_key.replace("_", " ").title()
                    )
                    value = field_data.get("value", "")
                    links = field_data.get("links", [])

                    content_lines.append(f"{original_name}: {value}")

                    if links:
                        for link in links:
                            content_lines.append(
                                f"  🔗 {link['text']} -> {link['url']}"
                            )

            content_lines.append("")

        # Add all links section
        if entity_data.get("all_links"):
            content_lines.append("ALL LINKS FOUND:")
            content_lines.append("-" * 40)
            for link in entity_data["all_links"]:
                content_lines.append(f"🔗 {link['text']} -> {link['url']}")
            content_lines.append("")

        # Add raw structured data as JSON for programmatic access (without HTML)
        json_data = {
            k: v
            for k, v in entity_data.items()
            if k not in ["raw_html"]  # Exclude raw HTML to reduce file size
        }

        content_lines.extend(
            [
                "=" * 80,
                "RAW STRUCTURED DATA (JSON):",
                "=" * 80,
                json.dumps(json_data, indent=2, ensure_ascii=False),
            ]
        )

        # Write to file
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(content_lines))

            print(f"  💾 Saved to: {file_path}")
            return str(file_path)

        except Exception as e:
            print(f"  ❌ Error saving {file_path}: {e}")
            return None

    def scrape_category(
        self, category: str, registry_file: Path, limit: Optional[int] = None
    ) -> List[str]:
        """Scrape all entities in a category."""
        print(f"\n🔍 Scraping detailed data for category: {category}")
        print(f"📁 Using registry: {registry_file}")

        # Load registry data
        registry_data = self.load_registry_file(registry_file)
        if not registry_data or "entities" not in registry_data:
            print(f"❌ No entities found in registry {registry_file}")
            return []

        entities = registry_data["entities"]
        if limit:
            entities = entities[:limit]

        print(f"📊 Found {len(entities)} entities to scrape")

        saved_files = []
        skipped_count = 0

        for i, entity in enumerate(entities, 1):
            entity_name = entity.get("name", "Unknown")
            entity_url = entity.get("url", "")
            entity_uuid = entity.get("uuid", "")

            if not entity_url:
                print(f"  ⚠️  Skipping entity without URL: {entity_name}")
                skipped_count += 1
                continue

            # Check if file already exists
            safe_name = re.sub(r"[^\w\s-]", "", entity_name)
            safe_name = re.sub(r"[-\s]+", "-", safe_name).strip("-")[:100]
            expected_filename = f"{entity_uuid}_{safe_name}.txt"
            expected_path = self.data_root / category / expected_filename

            if expected_path.exists():
                print(f"  ⏭️  Skipping existing file: {entity_name}")
                skipped_count += 1
                continue

            # Print progress
            percentage = (i / len(entities)) * 100
            print(f"  📈 Progress: {i}/{len(entities)} ({percentage:.1f}%)")

            # Scrape the entity
            entity_data = self.scrape_entity_details(entity_url, entity_name, category)

            if entity_data:
                saved_file = self.save_entity_data(
                    entity_data, category, entity_uuid, entity_name
                )
                if saved_file:
                    saved_files.append(saved_file)
            else:
                skipped_count += 1

            # Rate limiting
            if i < len(entities) and self.delay:
                time.sleep(self.delay)

        print(f"  ✅ Completed: {len(saved_files)} saved, {skipped_count} skipped")
        return saved_files

    def scrape_all_categories(
        self, limit_per_category: Optional[int] = None
    ) -> Dict[str, List[str]]:
        """Scrape all categories."""
        print("🚀 Starting detailed HazMap scraping...")
        print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        registry_files = self.find_latest_registry_files()

        if not registry_files:
            print("❌ No registry files found! Run the registry scraper first.")
            return {}

        print(f"📁 Found registry files for: {', '.join(registry_files.keys())}")

        all_saved_files = {}

        for category, registry_file in registry_files.items():
            try:
                saved_files = self.scrape_category(
                    category, registry_file, limit_per_category
                )
                all_saved_files[category] = saved_files
            except KeyboardInterrupt:
                print(f"\n⏹️  Scraping interrupted by user during {category}")
                break
            except Exception as e:
                print(f"❌ Error scraping category {category}: {e}")
                continue

        print(f"\n🎉 Detailed scraping complete!")
        print(f"⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Print summary
        total_files = sum(len(files) for files in all_saved_files.values())
        print(f"\n📊 Summary:")
        for category, files in all_saved_files.items():
            print(f"  {category}: {len(files)} files")
        print(f"  Total: {total_files} files")

        return all_saved_files


def main():
    """Main function to run the detailed scraper."""
    import argparse

    parser = argparse.ArgumentParser(description="Scrape detailed HazMap data")
    parser.add_argument(
        "--delay", type=float, default=1.0, help="Delay between requests (seconds)"
    )
    parser.add_argument(
        "--limit", type=int, help="Limit number of entities per category (for testing)"
    )
    parser.add_argument("--category", type=str, help="Scrape only this category")

    args = parser.parse_args()

    scraper = DetailedHazMapScraper(delay=args.delay)

    try:
        if args.category:
            # Scrape specific category
            registry_files = scraper.find_latest_registry_files()
            if args.category not in registry_files:
                print(f"❌ No registry file found for category: {args.category}")
                return

            saved_files = scraper.scrape_category(
                args.category, registry_files[args.category], args.limit
            )
            print(f"✅ Scraped {len(saved_files)} files for {args.category}")
        else:
            # Scrape all categories
            all_saved_files = scraper.scrape_all_categories(args.limit)
            print("✅ Scraping completed successfully!")

    except KeyboardInterrupt:
        print("\n⏹️  Scraping interrupted by user")
    except Exception as e:
        print(f"\n❌ Scraping failed: {e}")
        raise


if __name__ == "__main__":
    main()
