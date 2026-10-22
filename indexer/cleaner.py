"""
Wikitext Cleaning Pipeline (Tier B).

Strips:
1. XML/HTML comments: <!-- ... -->
2. References: <ref>...</ref> and <ref ... />
3. Nested templates: {{ ... }}
4. Wiki tables: {| ... |}
5. File and Category links: [[File:...]], [[Category:...]], [[Image:...]]
6. Wiki links: [[target|anchor]] -> anchor, [[target]] -> target
7. HTML tags: <div>, <p>, <span>, etc.
8. MediaWiki formatting quotes: '''''bold/italic''''', '''bold''', ''italic''
9. Normalizes whitespace and paragraph breaks.
"""
import re
from typing import Dict, Tuple

# Precompiled regex patterns for maximum stripping speed
COMMENT_RE = re.compile(r"<!--[\s\S]*?-->")
REF_TAG_RE = re.compile(r"<ref(?:\s+[^>]*?)?(?:/>|>[\s\S]*?</ref>)", re.IGNORECASE)
TABLE_RE = re.compile(r"\{\|[\s\S]*?\|\}")
FILE_CAT_RE = re.compile(r"\[\[(?:File|Image|Category):[\s\S]*?\]\]", re.IGNORECASE)
WIKI_LINK_PIPED_RE = re.compile(r"\[\[(?:[^|\]]*?)\|([^\]]+?)\]\]")
WIKI_LINK_SIMPLE_RE = re.compile(r"\[\[([^\]]+?)\]\]")
HTML_TAG_RE = re.compile(r"<[^>]+?>")
BOLD_ITALIC_RE = re.compile(r"'{2,5}")
EXTERNAL_LINK_RE = re.compile(r"\[https?://[^\s\]]+(?:\s+([^\]]+))?\]")
HEADER_RE = re.compile(r"^={2,6}\s*(.*?)\s*={2,6}$", re.MULTILINE)
WHITESPACE_RE = re.compile(r"[ \t]+")
NEWLINE_RE = re.compile(r"\n{3,}")


def strip_nested_templates(text: str) -> Tuple[str, int]:
    """
    Robustly removes nested MediaWiki templates {{ ... }}.
    Handles arbitrary nesting depth using a character stack.
    """
    if "{{" not in text:
        return text, 0

    chars = []
    i = 0
    n = len(text)
    depth = 0
    stripped_count = 0

    while i < n:
        if i + 1 < n and text[i] == "{" and text[i + 1] == "{":
            depth += 1
            i += 2
        elif i + 1 < n and text[i] == "}" and text[i + 1] == "}" and depth > 0:
            depth -= 1
            i += 2
            if depth == 0:
                stripped_count += 1
        else:
            if depth == 0:
                chars.append(text[i])
            i += 1

    return "".join(chars), stripped_count


def clean_wikitext(text: str) -> Tuple[str, Dict[str, int]]:
    """
    Cleans raw MediaWiki markup into clean article text.
    
    Returns:
        (cleaned_text, stats_dict)
    """
    if not text:
        return "", {"raw_chars": 0, "cleaned_chars": 0}

    stats = {"raw_chars": len(text)}

    # 1. Strip comments
    text, stats["comments_stripped"] = COMMENT_RE.subn(" ", text)

    # 2. Strip references
    text, stats["refs_stripped"] = REF_TAG_RE.subn(" ", text)

    # 3. Strip nested templates {{ ... }}
    text, stats["templates_stripped"] = strip_nested_templates(text)

    # 4. Strip wiki tables {| ... |}
    text, stats["tables_stripped"] = TABLE_RE.subn(" ", text)

    # 5. Strip File and Category links
    # Run multiple passes to handle any nested file brackets
    while FILE_CAT_RE.search(text):
        text = FILE_CAT_RE.sub(" ", text)

    # 6. Replace external links [http://url label] -> label
    text = EXTERNAL_LINK_RE.sub(r"\1", text)

    # 7. Replace wiki links: [[Page|Label]] -> Label, [[Page]] -> Page
    text = WIKI_LINK_PIPED_RE.sub(r"\1", text)
    text = WIKI_LINK_SIMPLE_RE.sub(r"\1", text)

    # 8. Strip HTML tags
    text = HTML_TAG_RE.sub(" ", text)

    # 9. Clean section headers == Title == -> Title
    text = HEADER_RE.sub(r"\1", text)

    # 10. Strip bold / italic quotes ('''bold''', ''italic'')
    text = BOLD_ITALIC_RE.sub("", text)

    # 11. Normalize whitespace and punctuation spacing
    text = WHITESPACE_RE.sub(" ", text)
    # Remove awkward spaces before punctuation caused by removed tags (e.g. 'word .' -> 'word.')
    text = re.sub(r"\s+([,.:;!?])", r"\1", text)
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(line for line in lines if line)
    text = NEWLINE_RE.sub("\n\n", text).strip()

    stats["cleaned_chars"] = len(text)
    return text, stats
