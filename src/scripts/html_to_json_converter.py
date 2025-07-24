#!/usr/bin/env python3
"""
High-performance HTML to JSON converter with UUID cross-referencing.

This script:
1. Loads all registry files to build a comprehensive UUID lookup table
2. Processes raw HTML files in parallel using multiprocessing
3. Converts HTML to structured JSON format
4. Cross-references entity names/URLs to add UUIDs for relationship mapping
5. Optimized for maximum speed with large datasets
"""

import json
import multiprocessing as mp
import re
import sys
import time
import yaml
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set

from bs4 import BeautifulSoup

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))


# Static helper functions for multiprocessing
def extract_text_content_static(element) -> str:
    """Extract clean text content from element."""
    if not element:
        return ""

    text = element.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def extract_links_from_element_static(element) -> List[Dict[str, str]]:
    """Extract all links from element."""
    if not element:
        return []

    links = []
    for link in element.find_all("a", href=True):
        link_text = extract_text_content_static(link)
        href = link.get("href")

        if href.startswith("/"):
            href = f"https://haz-map.com{href}"

        if link_text and href:
            links.append({"text": link_text, "url": href})

    return links


def normalize_section_name_static(section_name: str) -> str:
    """Normalize section name for consistent keys."""
    normalized = section_name.lower().strip()
    normalized = re.sub(r"[^\w\s]", "", normalized)
    return re.sub(r"\s+", "_", normalized)


def normalize_field_name_static(field_name: str) -> str:
    """Normalize field name for consistent keys."""
    normalized = re.sub(r"[^\w\s]", "", field_name)
    return re.sub(r"\s+", "_", normalized).lower().strip("_")


def find_cross_references_static(
    text: str,
    links: List[Dict[str, str]],
    uuid_lookup: Dict,
    url_lookup: Dict,
    name_variations: Dict,
) -> List[Dict[str, Any]]:
    """Find UUID cross-references in text and links."""
    cross_refs = []

    # Check direct URL matches first (most reliable)
    for link in links:
        url = link.get("url", "")
        if url in url_lookup:
            cross_refs.append(
                {
                    "type": "url_match",
                    "text": link.get("text", ""),
                    "url": url,
                    "confidence": 1.0,
                    **url_lookup[url],
                }
            )

    # Check for name matches in text
    text_lower = text.lower()

    # Direct name matches
    for name, entity_info in uuid_lookup.items():
        if name in text_lower:
            cross_refs.append(
                {"type": "name_match", "text": name, "confidence": 1.0, **entity_info}
            )

    # Fuzzy name matches (with confidence threshold)
    for variation, candidates in name_variations.items():
        if variation in text_lower and len(variation) > 4:  # Avoid very short matches
            for candidate in candidates:
                if candidate["match_confidence"] >= 0.7:  # High confidence threshold
                    cross_refs.append(
                        {
                            "type": "fuzzy_match",
                            "text": variation,
                            "matched_name": candidate["name"],
                            "confidence": candidate["match_confidence"],
                            "uuid": candidate["uuid"],
                            "category": candidate["category"],
                            "url": candidate["url"],
                        }
                    )

    # Remove duplicates based on UUID
    seen_uuids = set()
    unique_cross_refs = []
    for ref in cross_refs:
        uuid = ref.get("uuid")
        if uuid and uuid not in seen_uuids:
            seen_uuids.add(uuid)
            unique_cross_refs.append(ref)

    # Sort by confidence
    unique_cross_refs.sort(key=lambda x: x.get("confidence", 0), reverse=True)

    return unique_cross_refs


def extract_structured_data_static(
    soup: BeautifulSoup,
    metadata: Dict[str, str],
    uuid_lookup: Dict,
    url_lookup: Dict,
    name_variations: Dict,
) -> Dict[str, Any]:
    """Static function to extract structured data from HTML with cross-referencing."""
    data = {
        "metadata": metadata,
        "parsed_at": datetime.now().isoformat(),
        "title": "",
        "sections": {},
        "cross_references": [],
        "all_links": [],
    }

    # Extract title
    title_elem = soup.find("h1")
    if title_elem:
        data["title"] = extract_text_content_static(title_elem)

    # Find main content container
    content_container = soup.find("div", class_="item-details-container")
    if not content_container:
        return data

    # Extract all links first
    data["all_links"] = extract_links_from_element_static(content_container)

    # Extract sections and fields
    current_section = "general"
    rows = content_container.find_all("div", class_="row")

    for row in rows:
        # Check for section headers
        if "item-details-subheader" in row.get("class", []):
            section_header = extract_text_content_static(row)
            if section_header:
                current_section = normalize_section_name_static(section_header)
            continue

        # Initialize section
        if current_section not in data["sections"]:
            data["sections"][current_section] = {}

        # Extract field data
        cols = row.find_all("div", class_=re.compile(r"col-"))
        if len(cols) >= 2:
            field_name = extract_text_content_static(cols[0])
            field_value = extract_text_content_static(cols[1])
            field_links = extract_links_from_element_static(cols[1])

            if field_name and field_value:
                clean_field_name = normalize_field_name_static(field_name)

                # Find cross-references in this field
                field_cross_refs = find_cross_references_static(
                    field_value, field_links, uuid_lookup, url_lookup, name_variations
                )

                field_data = {
                    "original_name": field_name,
                    "value": field_value,
                    "links": field_links,
                    "cross_references": field_cross_refs,
                }

                data["sections"][current_section][clean_field_name] = field_data

    # Find overall cross-references from all text content
    all_text = " ".join(
        [
            data.get("title", ""),
            " ".join(
                [
                    field.get("value", "")
                    for section in data["sections"].values()
                    for field in section.values()
                ]
            ),
        ]
    )

    data["cross_references"] = find_cross_references_static(
        all_text, data["all_links"], uuid_lookup, url_lookup, name_variations
    )

    return data


def process_html_file(
    args: Tuple[Path, Dict[str, Any], Dict[str, Any], Dict[str, Any]],
) -> Optional[Tuple[str, Dict[str, Any]]]:
    """Process a single HTML file (designed for multiprocessing)."""
    html_file, uuid_lookup, url_lookup, name_variations = args

    try:
        # Read HTML file
        with open(html_file, "r", encoding="utf-8") as f:
            html_content = f.read()

        # Extract metadata from HTML comments
        metadata = {}
        if html_content.startswith("<!--"):
            comment_end = html_content.find("-->")
            if comment_end != -1:
                comment = html_content[:comment_end]
                for line in comment.split("\n"):
                    if ":" in line:
                        key, value = line.split(":", 1)
                        key = key.strip().lower().replace(" ", "_")
                        metadata[key] = value.strip()

        # Parse HTML
        soup = BeautifulSoup(html_content, "html.parser")

        # Extract structured data
        data = extract_structured_data_static(
            soup, metadata, uuid_lookup, url_lookup, name_variations
        )

        # Generate output filename
        category = metadata.get("category", "unknown")
        entity_uuid = metadata.get("uuid", "unknown")
        entity_name = metadata.get("entity_name", html_file.stem)

        safe_name = re.sub(r"[^\w\s-]", "", entity_name)
        safe_name = re.sub(r"[-\s]+", "-", safe_name).strip("-")[:100]
        output_filename = f"{entity_uuid}_{safe_name}.json"

        return output_filename, data

    except Exception as e:
        print(f"❌ Error processing {html_file}: {e}")
        return None


class FastHtmlToJsonConverter:
    """High-performance HTML to JSON converter with UUID cross-referencing."""

    def __init__(self, max_workers: Optional[int] = None):
        """Initialize the converter.

        Args:
            max_workers: Number of parallel processes (default: CPU count)
        """
        self.max_workers = max_workers or mp.cpu_count()
        self.data_root = Path("data")
        self.raw_html_dir = self.data_root / "raw_html"
        self.json_output_dir = self.data_root / "formatted" / "json"

        # Cross-reference lookup tables
        self.uuid_lookup = {}  # name -> uuid
        self.url_lookup = {}  # url -> uuid
        self.name_variations = {}  # variations of names for fuzzy matching

        # Ensure output directory exists
        self.json_output_dir.mkdir(parents=True, exist_ok=True)

    def build_cross_reference_tables(self) -> None:
        """Build comprehensive lookup tables from all registry files for UUID cross-referencing."""
        print("🔧 Building cross-reference tables...")

        registry_dir = self.data_root / "registry"
        if not registry_dir.exists():
            print("❌ No registry directory found!")
            return

        total_entities = 0

        for registry_file in registry_dir.glob("*_registry_*.yml"):
            try:
                with open(registry_file, "r", encoding="utf-8") as f:
                    registry_data = yaml.safe_load(f)

                if not registry_data or "entities" not in registry_data:
                    continue

                category = registry_file.name.split("_registry_")[0]
                entities = registry_data["entities"]

                for entity in entities:
                    name = entity.get("name", "").strip()
                    url = entity.get("url", "").strip()
                    uuid = entity.get("uuid", "").strip()

                    if not all([name, url, uuid]):
                        continue

                    # Direct name lookup
                    self.uuid_lookup[name.lower()] = {
                        "uuid": uuid,
                        "name": name,
                        "url": url,
                        "category": category,
                    }

                    # URL lookup
                    self.url_lookup[url] = {
                        "uuid": uuid,
                        "name": name,
                        "url": url,
                        "category": category,
                    }

                    # Name variations for better matching
                    name_variations = self._generate_name_variations(name)
                    for variation in name_variations:
                        if variation not in self.name_variations:
                            self.name_variations[variation] = []
                        self.name_variations[variation].append(
                            {
                                "uuid": uuid,
                                "name": name,
                                "url": url,
                                "category": category,
                                "match_confidence": self._calculate_match_confidence(
                                    name, variation
                                ),
                            }
                        )

                    total_entities += 1

                print(f"  📁 Loaded {len(entities)} entities from {category}")

            except Exception as e:
                print(f"❌ Error loading {registry_file}: {e}")

        print(f"✅ Built lookup tables with {total_entities} entities")
        print(f"  📊 Direct lookups: {len(self.uuid_lookup)}")
        print(f"  📊 URL lookups: {len(self.url_lookup)}")
        print(f"  📊 Name variations: {len(self.name_variations)}")

    def _generate_name_variations(self, name: str) -> Set[str]:
        """Generate name variations for better matching."""
        variations = set()
        name_lower = name.lower()

        # Original name
        variations.add(name_lower)

        # Remove common suffixes/prefixes
        for suffix in [" compounds", " and compounds", " (total)", " dust", " fumes"]:
            if name_lower.endswith(suffix):
                variations.add(name_lower[: -len(suffix)].strip())

        # Remove parenthetical content
        paren_match = re.match(r"^([^(]+)", name_lower)
        if paren_match:
            variations.add(paren_match.group(1).strip())

        # Remove special characters and normalize
        normalized = re.sub(r"[^\w\s]", " ", name_lower)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        variations.add(normalized)

        # Split on common delimiters
        for delimiter in [",", ";", "/", " or ", " and "]:
            if delimiter in name_lower:
                parts = name_lower.split(delimiter)
                for part in parts:
                    part = part.strip()
                    if len(part) > 2:  # Avoid very short matches
                        variations.add(part)

        return {v for v in variations if len(v) > 2}

    def _calculate_match_confidence(self, original: str, variation: str) -> float:
        """Calculate match confidence between original name and variation."""
        if original.lower() == variation.lower():
            return 1.0

        # Simple confidence based on length similarity and character overlap
        len_ratio = min(len(original), len(variation)) / max(
            len(original), len(variation)
        )

        # Count common characters
        orig_chars = set(original.lower())
        var_chars = set(variation.lower())
        char_overlap = len(orig_chars & var_chars) / len(orig_chars | var_chars)

        return (len_ratio + char_overlap) / 2

    def convert_all_html_files(
        self, limit: Optional[int] = None, category: Optional[str] = None
    ) -> Dict[str, int]:
        """Convert all HTML files to JSON with parallel processing."""
        print("🚀 Starting high-performance HTML to JSON conversion...")
        start_time = time.time()

        # Build cross-reference tables
        self.build_cross_reference_tables()

        # Find HTML files to process
        html_files = []
        categories_to_process = []

        if category:
            category_dir = self.raw_html_dir / category
            if category_dir.exists():
                categories_to_process = [category]
                html_files.extend(list(category_dir.glob("*.html")))
        else:
            for cat_dir in self.raw_html_dir.iterdir():
                if cat_dir.is_dir():
                    categories_to_process.append(cat_dir.name)
                    html_files.extend(list(cat_dir.glob("*.html")))

        if limit:
            html_files = html_files[:limit]

        if not html_files:
            print("❌ No HTML files found to process!")
            return {}

        print(f"📁 Found {len(html_files)} HTML files to process")
        print(f"🔧 Using {self.max_workers} parallel processes")

        # Prepare arguments for multiprocessing
        process_args = [
            (html_file, self.uuid_lookup, self.url_lookup, self.name_variations)
            for html_file in html_files
        ]

        # Process files in parallel
        results = {}
        processed_count = 0
        error_count = 0

        # Ensure category output directories exist
        for cat in categories_to_process:
            (self.json_output_dir / cat).mkdir(parents=True, exist_ok=True)
            results[cat] = 0

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(process_html_file, args): args[0]
                for args in process_args
            }

            # Process completed tasks
            for future in as_completed(future_to_file):
                html_file = future_to_file[future]

                try:
                    result = future.result()
                    if result:
                        output_filename, data = result

                        # Determine category from file path
                        file_category = html_file.parent.name
                        output_path = (
                            self.json_output_dir / file_category / output_filename
                        )

                        # Save JSON file
                        with open(output_path, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)

                        processed_count += 1
                        results[file_category] += 1

                        # Progress indicator
                        if processed_count % 100 == 0:
                            elapsed = time.time() - start_time
                            rate = processed_count / elapsed
                            remaining = len(html_files) - processed_count
                            eta = remaining / rate if rate > 0 else 0
                            print(
                                f"  📈 Processed {processed_count}/{len(html_files)} files ({rate:.1f} files/sec, ETA: {eta:.1f}s)"
                            )

                    else:
                        error_count += 1

                except Exception as e:
                    print(f"❌ Error processing {html_file}: {e}")
                    error_count += 1

        elapsed = time.time() - start_time
        print(f"\n✅ Conversion complete!")
        print(f"⏱️  Total time: {elapsed:.2f} seconds")
        print(f"📊 Processed: {processed_count} files")
        print(f"❌ Errors: {error_count} files")
        print(f"🚀 Rate: {processed_count/elapsed:.1f} files/second")

        print(f"\n📊 Results by category:")
        for cat, count in results.items():
            print(f"  {cat}: {count} files")

        return results


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert HTML files to JSON with UUID cross-referencing"
    )
    parser.add_argument("--category", type=str, help="Process only this category")
    parser.add_argument(
        "--limit", type=int, help="Limit number of files to process (for testing)"
    )
    parser.add_argument(
        "--workers", type=int, help="Number of parallel workers (default: CPU count)"
    )

    args = parser.parse_args()

    converter = FastHtmlToJsonConverter(max_workers=args.workers)

    try:
        results = converter.convert_all_html_files(
            limit=args.limit, category=args.category
        )
        total_files = sum(results.values())

        if total_files > 0:
            print("🎉 HTML to JSON conversion completed successfully!")
        else:
            print("❌ No files were processed")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⏹️  Conversion interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Conversion failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
