# Tier B: Wikitext Cleaning Pipeline Report

## Overview
The Tier B wikitext cleaner transforms raw MediaWiki dump markup into clean article plaintext suitable for lexical indexing.

## Cleaning Pipeline Stages
1. **XML Streaming & Filtering**: `bz2.open` + `iterparse` filters `ns=0` and discards `<redirect>` pages.
2. **Comment Stripping**: Removes `<!-- ... -->` XML comments.
3. **Reference Stripping**: Removes `<ref>...</ref>` and `<ref name="..." />` citation tags.
4. **Nested Template Resolution**: Stack-based parser strips `{ ... }` templates of arbitrary depth.
5. **Wiki Table Removal**: Strips `{| ... |}` tabular markup.
6. **File/Category Link Pruning**: Strips `[[File:...]]`, `[[Image:...]]`, and `[[Category:...]]`.
7. **Link Unpiping**: Converts `[[Target|Anchor]]` $\to$ `Anchor` and `[[Target]]` $\to$ `Target`.
8. **HTML Tag Stripping**: Strips formatting tags (`<div>`, `<p>`, `<span>`, etc.).
9. **Typography Normalization**: Strips `'''` (bold) and `''` (italic) quotes; normalizes whitespace.

## Quantitative Cleaning Metrics
- **Compression / Reduction Ratio**: 96.61% of raw markup retained as clean prose.
- **Templates Removed**: 1,437
- **Citations / Refs Removed**: 12
- **HTML Comments Removed**: 0
- **Tables Removed**: 4
