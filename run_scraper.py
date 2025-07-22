#!/usr/bin/env python3
"""
Advanced CLI for processing HazMap data with flexible input sources and output formats.

This script can:
1. Process raw HTML files or read from registry to scrape fresh data
2. Output in multiple formats: clean, structured, or JSON
3. Handle individual files, specific categories, or run all
4. Support limits for testing and partial processing
"""

import argparse
import json
import re
import sys
import time
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

import requests
from bs4 import BeautifulSoup

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))


class HazMapProcessor:
    """Advanced processor for HazMap data with flexible input/output options."""

    def __init__(self, delay: float = 1.0):
        """Initialize the processor."""
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (compatible; HazMapProcessor/2.0; +https://github.com/hazardos-ai/hazmap-scraper)"
            }
        )

        # Define paths
        self.data_root = Path("data")
        self.registry_dir = self.data_root / "registry"
        self.raw_html_dir = self.data_root / "raw_html"
        self.formatted_dir = self.data_root / "formatted"

        # Ensure output directories exist
        self.create_output_directories()

    def create_output_directories(self):
        """Create output directories for different formats."""
        formats = ["clean", "structured", "json"]
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

        for format_type in formats:
            format_dir = self.formatted_dir / format_type
            format_dir.mkdir(parents=True, exist_ok=True)

            for category in categories:
                category_dir = format_dir / category
                category_dir.mkdir(parents=True, exist_ok=True)

    def find_latest_registry_files(self) -> Dict[str, Path]:
        """Find the latest registry file for each category."""
        registry_files = {}

        if not self.registry_dir.exists():
            return {}

        for registry_file in self.registry_dir.glob("*_registry_*.yml"):
            category = registry_file.name.split("_registry_")[0]

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

    def load_registry_file(self, registry_path: Path) -> Dict[str, Any]:
        """Load a registry file and return the parsed data."""
        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"❌ Error loading registry {registry_path}: {e}")
            return {}

    def extract_text_content(self, element) -> str:
        """Extract clean text content from a BeautifulSoup element."""
        if not element:
            return ""

        text = element.get_text(separator=" ", strip=True)
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

            if href.startswith("/"):
                href = f"https://haz-map.com{href}"

            if link_text and href:
                links.append({"text": link_text, "url": href})

        return links

    def parse_html_content(self, html_content: str, url: str = "") -> Dict[str, Any]:
        """Parse HTML content and extract structured data."""
        soup = BeautifulSoup(html_content, "html.parser")

        data = {
            "url": url,
            "parsed_at": datetime.now().isoformat(),
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
            return data

        # Extract all text content for clean processing
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

                    data["sections"][current_section][clean_field_name] = field_data
                    clean_text_lines.append(f"{field_name}: {field_value}")

                    for link in field_links:
                        clean_text_lines.append(f"  -> {link['text']}: {link['url']}")

            elif len(cols) == 1:
                content = self.extract_text_content(cols[0])
                links = self.extract_links_from_element(cols[0])

                if content:
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

        # Handle nested structures (subrows)
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
        data["clean_content"] = "\n".join(clean_text_lines)

        return data

    def process_html_file(self, html_file: Path) -> Optional[Dict[str, Any]]:
        """Process a single HTML file."""
        try:
            with open(html_file, "r", encoding="utf-8") as f:
                html_content = f.read()

            # Extract metadata from HTML comments if present
            url = ""
            entity_name = ""
            category = ""
            uuid = ""

            if html_content.startswith("<!--"):
                comment_end = html_content.find("-->")
                if comment_end != -1:
                    comment = html_content[:comment_end]
                    for line in comment.split("\n"):
                        if "Scraped from:" in line:
                            url = line.split("Scraped from:")[1].strip()
                        elif "Entity Name:" in line:
                            entity_name = line.split("Entity Name:")[1].strip()
                        elif "Category:" in line:
                            category = line.split("Category:")[1].strip()
                        elif "UUID:" in line:
                            uuid = line.split("UUID:")[1].strip()

            # Parse the HTML content
            parsed_data = self.parse_html_content(html_content, url)
            parsed_data.update(
                {
                    "entity_name": entity_name,
                    "category": category,
                    "uuid": uuid,
                    "source_file": str(html_file),
                }
            )

            return parsed_data

        except Exception as e:
            print(f"❌ Error processing HTML file {html_file}: {e}")
            return None

    def scrape_fresh_data(
        self, entity_url: str, entity_name: str, category: str
    ) -> Optional[Dict[str, Any]]:
        """Scrape fresh data from a URL."""
        try:
            print(f"  🔍 Scraping: {entity_name}")

            response = self.session.get(entity_url, timeout=30)
            response.raise_for_status()

            parsed_data = self.parse_html_content(response.text, entity_url)
            parsed_data.update(
                {
                    "entity_name": entity_name,
                    "category": category,
                    "source": "fresh_scrape",
                }
            )

            return parsed_data

        except requests.exceptions.RequestException as e:
            print(f"  ❌ Network error scraping {entity_url}: {e}")
            return None
        except Exception as e:
            print(f"  ❌ Error scraping {entity_url}: {e}")
            return None

    def format_output(self, data: Dict[str, Any], format_type: str) -> str:
        """Format the parsed data according to the specified format."""
        if format_type == "json":
            return json.dumps(data, indent=2, ensure_ascii=False)

        elif format_type == "clean":
            lines = [
                f"Entity: {data.get('entity_name', 'Unknown')}",
                f"Category: {data.get('category', 'Unknown')}",
                f"URL: {data.get('url', '')}",
                f"Processed At: {data.get('parsed_at', '')}",
                "=" * 80,
                "",
            ]

            if data.get("clean_content"):
                lines.extend(["CLEAN CONTENT:", "-" * 40, data["clean_content"], ""])

            return "\n".join(lines)

        elif format_type == "structured":
            lines = [
                f"Entity: {data.get('entity_name', 'Unknown')}",
                f"Category: {data.get('category', 'Unknown')}",
                f"URL: {data.get('url', '')}",
                f"Processed At: {data.get('parsed_at', '')}",
                "=" * 80,
                "",
            ]

            if data.get("sections"):
                lines.append("STRUCTURED DATA:")
                lines.append("-" * 40)

                for section_name, section_data in data["sections"].items():
                    section_title = section_name.replace("_", " ").title()
                    lines.append(f"\n[{section_title}]")

                    for field_key, field_data in section_data.items():
                        original_name = field_data.get(
                            "original_name", field_key.replace("_", " ").title()
                        )
                        value = field_data.get("value", "")
                        links = field_data.get("links", [])

                        lines.append(f"{original_name}: {value}")

                        if links:
                            for link in links:
                                lines.append(f"  🔗 {link['text']} -> {link['url']}")

            return "\n".join(lines)

        else:
            raise ValueError(f"Unknown format type: {format_type}")

    def save_output(
        self,
        data: Dict[str, Any],
        format_type: str,
        entity_uuid: str,
        entity_name: str,
        category: str,
    ) -> Optional[str]:
        """Save the formatted output to a file."""
        # Create safe filename
        safe_name = re.sub(r"[^\w\s-]", "", entity_name)
        safe_name = re.sub(r"[-\s]+", "-", safe_name)
        safe_name = safe_name.strip("-")[:100]

        # Determine file extension
        ext = "json" if format_type == "json" else "txt"
        filename = f"{entity_uuid}_{safe_name}.{ext}"

        output_dir = self.formatted_dir / format_type / category
        output_file = output_dir / filename

        try:
            formatted_content = self.format_output(data, format_type)

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(formatted_content)

            print(f"  💾 Saved: {output_file}")
            return str(output_file)

        except Exception as e:
            print(f"  ❌ Error saving {output_file}: {e}")
            return None

    def process_single_file(self, file_path: str, format_type: str) -> bool:
        """Process a single HTML file."""
        html_file = Path(file_path)

        if not html_file.exists():
            print(f"❌ File not found: {file_path}")
            return False

        print(f"🔍 Processing file: {html_file}")

        data = self.process_html_file(html_file)
        if not data:
            return False

        entity_uuid = data.get("uuid", "unknown")
        entity_name = data.get("entity_name", "unknown")
        category = data.get("category", "unknown")

        saved_file = self.save_output(
            data, format_type, entity_uuid, entity_name, category
        )
        return saved_file is not None

    def process_category_from_html(
        self, category: str, format_type: str, limit: Optional[int] = None
    ) -> int:
        """Process all HTML files for a category."""
        html_category_dir = self.raw_html_dir / category

        if not html_category_dir.exists():
            print(f"❌ HTML directory not found: {html_category_dir}")
            return 0

        html_files = list(html_category_dir.glob("*.html"))
        if limit:
            html_files = html_files[:limit]

        print(f"🔍 Processing {len(html_files)} HTML files for {category}")

        processed_count = 0
        for html_file in html_files:
            data = self.process_html_file(html_file)
            if data:
                entity_uuid = data.get("uuid", "unknown")
                entity_name = data.get("entity_name", "unknown")

                if self.save_output(
                    data, format_type, entity_uuid, entity_name, category
                ):
                    processed_count += 1

        print(f"✅ Processed {processed_count}/{len(html_files)} files for {category}")
        return processed_count

    def process_category_from_registry(
        self, category: str, format_type: str, limit: Optional[int] = None
    ) -> int:
        """Process entities from registry (fresh scraping)."""
        registry_files = self.find_latest_registry_files()

        if category not in registry_files:
            print(f"❌ No registry found for category: {category}")
            return 0

        registry_data = self.load_registry_file(registry_files[category])
        if not registry_data or "entities" not in registry_data:
            print(f"❌ No entities found in registry for {category}")
            return 0

        entities = registry_data["entities"]
        if limit:
            entities = entities[:limit]

        print(f"🔍 Processing {len(entities)} entities from registry for {category}")

        processed_count = 0
        for i, entity in enumerate(entities, 1):
            entity_name = entity.get("name", "Unknown")
            entity_url = entity.get("url", "")
            entity_uuid = entity.get("uuid", "")

            if not entity_url:
                print(f"  ⚠️  Skipping entity without URL: {entity_name}")
                continue

            # Print progress
            if len(entities) > 10:
                percentage = (i / len(entities)) * 100
                print(f"  📈 Progress: {i}/{len(entities)} ({percentage:.1f}%)")

            data = self.scrape_fresh_data(entity_url, entity_name, category)
            if data:
                if self.save_output(
                    data, format_type, entity_uuid, entity_name, category
                ):
                    processed_count += 1

            # Rate limiting
            if i < len(entities) and self.delay:
                time.sleep(self.delay)

        print(f"✅ Processed {processed_count}/{len(entities)} entities for {category}")
        return processed_count

    def process_all_categories(
        self, source: str, format_type: str, limit: Optional[int] = None
    ) -> Dict[str, int]:
        """Process all categories from the specified source."""
        if source == "html":
            available_categories = [
                d.name for d in self.raw_html_dir.iterdir() if d.is_dir()
            ]
        else:  # registry
            available_categories = list(self.find_latest_registry_files().keys())

        if not available_categories:
            print(f"❌ No categories found for source: {source}")
            return {}

        print(
            f"🚀 Processing all categories from {source}: {', '.join(available_categories)}"
        )

        results = {}
        for category in available_categories:
            try:
                if source == "html":
                    count = self.process_category_from_html(
                        category, format_type, limit
                    )
                else:
                    count = self.process_category_from_registry(
                        category, format_type, limit
                    )
                results[category] = count
            except Exception as e:
                print(f"❌ Error processing category {category}: {e}")
                results[category] = 0

        return results


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="Process HazMap data with flexible input sources and output formats",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all HTML files as JSON (default)
  python run_scraper.py
  
  # Process specific category from HTML
  python run_scraper.py --source html --category agents --format json
  
  # Process from registry with limit
  python run_scraper.py --source registry --category diseases --limit 10 --format structured
  
  # Process single file
  python run_scraper.py --file data/raw_html/agents/uuid_filename.html --format clean
  
  # Process all with custom settings
  python run_scraper.py --source html --format structured --limit 5 --delay 2.0
        """,
    )

    parser.add_argument(
        "--source",
        choices=["html", "registry"],
        default="html",
        help="Data source: 'html' to process existing HTML files, 'registry' to scrape fresh data (default: html)",
    )

    parser.add_argument(
        "--format",
        choices=["clean", "structured", "json"],
        default="json",
        help="Output format (default: json)",
    )

    parser.add_argument(
        "--category", help="Process specific category (agents, diseases, etc.)"
    )

    parser.add_argument("--file", help="Process single HTML file")

    parser.add_argument(
        "--limit",
        type=int,
        help="Limit number of files/entities to process (useful for testing)",
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Delay between requests in seconds when using registry source (default: 1.0)",
    )

    args = parser.parse_args()

    # Initialize processor
    processor = HazMapProcessor(delay=args.delay)

    print("🚀 HazMap Data Processor")
    print("=" * 50)
    print(f"Source: {args.source}")
    print(f"Format: {args.format}")
    print(f"Category: {args.category or 'all'}")
    print(f"File: {args.file or 'none'}")
    print(f"Limit: {args.limit or 'none'}")
    print("=" * 50)

    try:
        if args.file:
            # Process single file
            success = processor.process_single_file(args.file, args.format)
            if success:
                print("✅ File processed successfully!")
            else:
                print("❌ Failed to process file")
                sys.exit(1)

        elif args.category:
            # Process specific category
            if args.source == "html":
                count = processor.process_category_from_html(
                    args.category, args.format, args.limit
                )
            else:
                count = processor.process_category_from_registry(
                    args.category, args.format, args.limit
                )

            if count > 0:
                print(f"✅ Processed {count} items for {args.category}")
            else:
                print(f"❌ No items processed for {args.category}")
                sys.exit(1)

        else:
            # Process all categories
            results = processor.process_all_categories(
                args.source, args.format, args.limit
            )

            total_processed = sum(results.values())
            print(f"\n📊 Summary:")
            for category, count in results.items():
                print(f"  {category}: {count} items")
            print(f"  Total: {total_processed} items")

            if total_processed > 0:
                print("✅ Processing completed successfully!")
            else:
                print("❌ No items processed")
                sys.exit(1)

    except KeyboardInterrupt:
        print("\n⏹️  Processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Processing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
