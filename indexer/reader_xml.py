"""
Streaming XML Dump Reader for Wikipedia (Tier B).

Reads .xml.bz2 dumps using streaming bz2 decompression and xml.etree.ElementTree.iterparse:
- Keeps only namespace 0 (ns=0, main encyclopedia articles).
- Skips redirect pages.
- Cleans wikitext using the Tier B wikitext cleaner.
- Never unpacks the full dump to disk, maintaining O(1) RAM usage.
- Emits cleaning statistics report.
"""
import bz2
from pathlib import Path
from typing import Generator, Optional, Tuple, Union
import xml.etree.ElementTree as ET

from indexer.cleaner import clean_wikitext


def stream_wikipedia_xml(
    xml_bz2_path: Union[str, Path],
    max_articles: Optional[int] = None,
) -> Generator[Tuple[int, str, str], None, None]:
    """
    Streams cleaned Wikipedia articles from a .xml.bz2 dump.
    
    Yields:
        (doc_id, title, clean_text)
    """
    path = Path(xml_bz2_path)
    if not path.exists():
        raise FileNotFoundError(f"XML dump not found: {path}")

    doc_id = 0
    
    with bz2.open(path, "rb") as bz2_file:
        context = ET.iterparse(bz2_file, events=("end",))
        
        title = None
        ns = None
        is_redirect = False
        text = None

        for event, elem in context:
            tag = elem.tag.split("}")[-1]  # strip MediaWiki XML namespace
            
            if tag == "title":
                title = elem.text or ""
            elif tag == "ns":
                ns = elem.text or ""
            elif tag == "redirect":
                is_redirect = True
            elif tag == "text":
                text = elem.text or ""
            elif tag == "page":
                # Process complete page element
                if ns == "0" and not is_redirect and title and text:
                    cleaned_text, _ = clean_wikitext(text)
                    if cleaned_text:
                        yield doc_id, title, cleaned_text
                        doc_id += 1
                        if max_articles is not None and doc_id >= max_articles:
                            elem.clear()
                            break

                # Reset page state and clear XML element from memory
                title = None
                ns = None
                is_redirect = False
                text = None
                elem.clear()


def generate_cleaning_report(
    sample_texts: list,
    output_path: str = "report/cleaning_report.md",
) -> Path:
    """Generates a quantitative wikitext cleaning evaluation report."""
    total_raw = 0
    total_cleaned = 0
    total_templates = 0
    total_comments = 0
    total_refs = 0
    total_tables = 0

    for raw in sample_texts:
        cleaned, stats = clean_wikitext(raw)
        total_raw += stats["raw_chars"]
        total_cleaned += stats["cleaned_chars"]
        total_templates += stats.get("templates_stripped", 0)
        total_comments += stats.get("comments_stripped", 0)
        total_refs += stats.get("refs_stripped", 0)
        total_tables += stats.get("tables_stripped", 0)

    ratio = (total_cleaned / total_raw) if total_raw > 0 else 1.0

    report = f"""# Tier B: Wikitext Cleaning Pipeline Report

## Overview
The Tier B wikitext cleaner transforms raw MediaWiki dump markup into clean article plaintext suitable for lexical indexing.

## Cleaning Pipeline Stages
1. **XML Streaming & Filtering**: `bz2.open` + `iterparse` filters `ns=0` and discards `<redirect>` pages.
2. **Comment Stripping**: Removes `<!-- ... -->` XML comments.
3. **Reference Stripping**: Removes `<ref>...</ref>` and `<ref name="..." />` citation tags.
4. **Nested Template Resolution**: Stack-based parser strips `{{ ... }}` templates of arbitrary depth.
5. **Wiki Table Removal**: Strips `{{| ... |}}` tabular markup.
6. **File/Category Link Pruning**: Strips `[[File:...]]`, `[[Image:...]]`, and `[[Category:...]]`.
7. **Link Unpiping**: Converts `[[Target|Anchor]]` $\\to$ `Anchor` and `[[Target]]` $\\to$ `Target`.
8. **HTML Tag Stripping**: Strips formatting tags (`<div>`, `<p>`, `<span>`, etc.).
9. **Typography Normalization**: Strips `'''` (bold) and `''` (italic) quotes; normalizes whitespace.

## Quantitative Cleaning Metrics
- **Compression / Reduction Ratio**: {ratio:.2%} of raw markup retained as clean prose.
- **Templates Removed**: {total_templates:,}
- **Citations / Refs Removed**: {total_refs:,}
- **HTML Comments Removed**: {total_comments:,}
- **Tables Removed**: {total_tables:,}
"""
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(report)
    return out_file
