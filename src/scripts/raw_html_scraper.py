#!/usr/bin/env python3
"""
Raw HTML scraper for haz-map.com that saves the complete HTML source
for each entity page to individual HTML files.

This script:
1. Loads existing registry files to get entity URLs
2. Downloads each page and saves the complete HTML
3. Organizes files by category (agents, diseases, etc.)
4. Preserves original HTML for future processing
"""

import re
import sys
import time
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import requests

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))


class RawHtmlScraper:
    """Raw HTML scraper for haz-map.com entity data."""

    def __init__(self, delay: Optional[float] = 1.0):
        """Initialize the scraper.

        Args:
            delay: Delay between requests in seconds to be respectful
        """
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (compatible; HazMapRawScraper/1.0; +https://github.com/hazardos-ai/hazmap-scraper)"
            }
        )

        # Create data directories
        self.data_root = Path("data")
        self.html_root = self.data_root / "raw_html"
        self.create_directories()

    def create_directories(self):
        """Create necessary directories for storing raw HTML data."""
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
            category_dir = self.html_root / category
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

    def scrape_entity_html(
        self, entity_url: str, entity_name: str, category: str
    ) -> Optional[str]:
        """Download the raw HTML for a single entity page."""
        try:
            print(f"  🔍 Downloading: {entity_name}")

            response = self.session.get(entity_url, timeout=30)
            response.raise_for_status()

            return response.text

        except requests.exceptions.RequestException as e:
            print(f"  ❌ Network error downloading {entity_url}: {e}")
            return None
        except Exception as e:
            print(f"  ❌ Error downloading {entity_url}: {e}")
            return None

    def save_html_file(
        self,
        html_content: str,
        entity_url: str,
        category: str,
        entity_uuid: str,
        entity_name: str,
    ):
        """Save HTML content to a file."""
        # Create safe filename
        safe_name = re.sub(r"[^\w\s-]", "", entity_name)
        safe_name = re.sub(r"[-\s]+", "-", safe_name)
        safe_name = safe_name.strip("-")[:100]  # Limit length

        filename = f"{entity_uuid}_{safe_name}.html"
        file_path = self.html_root / category / filename

        # Add metadata as HTML comments at the top
        metadata_comment = f"""<!--
Scraped from: {entity_url}
Entity Name: {entity_name}
Category: {category}
UUID: {entity_uuid}
Scraped At: {datetime.now().isoformat()}
-->

"""

        # Combine metadata and original HTML
        full_content = metadata_comment + html_content

        # Write to file
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(full_content)

            print(f"  💾 Saved to: {file_path}")
            return str(file_path)

        except Exception as e:
            print(f"  ❌ Error saving {file_path}: {e}")
            return None

    def scrape_category(
        self, category: str, registry_file: Path, limit: Optional[int] = None
    ) -> List[str]:
        """Scrape all entities in a category."""
        print(f"\n🔍 Downloading raw HTML for category: {category}")
        print(f"📁 Using registry: {registry_file}")

        # Load registry data
        registry_data = self.load_registry_file(registry_file)
        if not registry_data or "entities" not in registry_data:
            print(f"❌ No entities found in registry {registry_file}")
            return []

        entities = registry_data["entities"]
        if limit:
            entities = entities[:limit]

        print(f"📊 Found {len(entities)} entities to download")

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
            expected_filename = f"{entity_uuid}_{safe_name}.html"
            expected_path = self.html_root / category / expected_filename

            if expected_path.exists():
                print(f"  ⏭️  Skipping existing file: {entity_name}")
                skipped_count += 1
                continue

            # Print progress
            percentage = (i / len(entities)) * 100
            print(f"  📈 Progress: {i}/{len(entities)} ({percentage:.1f}%)")

            # Download the HTML
            html_content = self.scrape_entity_html(entity_url, entity_name, category)

            if html_content:
                saved_file = self.save_html_file(
                    html_content, entity_url, category, entity_uuid, entity_name
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
        print("🚀 Starting raw HTML download from HazMap...")
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
                print(f"\n⏹️  Download interrupted by user during {category}")
                break
            except Exception as e:
                print(f"❌ Error downloading category {category}: {e}")
                continue

        print(f"\n🎉 Raw HTML download complete!")
        print(f"⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Print summary
        total_files = sum(len(files) for files in all_saved_files.values())
        print(f"\n📊 Summary:")
        for category, files in all_saved_files.items():
            print(f"  {category}: {len(files)} files")
        print(f"  Total: {total_files} files")

        # Print file sizes
        total_size = 0
        for category in all_saved_files.keys():
            category_dir = self.html_root / category
            if category_dir.exists():
                category_size = sum(
                    f.stat().st_size for f in category_dir.glob("*.html")
                )
                total_size += category_size
                print(f"  {category} size: {category_size / (1024*1024):.1f} MB")

        print(f"  Total size: {total_size / (1024*1024):.1f} MB")

        return all_saved_files


def main():
    """Main function to run the raw HTML scraper."""
    import argparse

    parser = argparse.ArgumentParser(description="Download raw HTML from HazMap")
    parser.add_argument(
        "--delay", type=float, default=1.0, help="Delay between requests (seconds)"
    )
    parser.add_argument(
        "--limit", type=int, help="Limit number of entities per category (for testing)"
    )
    parser.add_argument("--category", type=str, help="Download only this category")

    args = parser.parse_args()

    scraper = RawHtmlScraper(delay=args.delay)

    try:
        if args.category:
            # Download specific category
            registry_files = scraper.find_latest_registry_files()
            if args.category not in registry_files:
                print(f"❌ No registry file found for category: {args.category}")
                return

            saved_files = scraper.scrape_category(
                args.category, registry_files[args.category], args.limit
            )
            print(f"✅ Downloaded {len(saved_files)} files for {args.category}")
        else:
            # Download all categories
            all_saved_files = scraper.scrape_all_categories(args.limit)
            print("✅ Download completed successfully!")

    except KeyboardInterrupt:
        print("\n⏹️  Download interrupted by user")
    except Exception as e:
        print(f"\n❌ Download failed: {e}")
        raise


if __name__ == "__main__":
    main()
