"""
Unit tests for Tier B wikitext cleaning pipeline.
"""
from indexer.cleaner import clean_wikitext, strip_nested_templates


def test_strip_nested_templates():
    raw = "Hello {{Infobox {{nested}} data}} World"
    cleaned, count = strip_nested_templates(raw)
    assert cleaned.strip() == "Hello  World"
    assert count == 1


def test_strip_comments_and_refs():
    raw = "The Sun <!-- hidden note --> is a star<ref>Reference text</ref>."
    cleaned, _ = clean_wikitext(raw)
    assert "hidden note" not in cleaned
    assert "Reference text" not in cleaned
    assert "The Sun is a star." in cleaned


def test_strip_tables():
    raw = "Start {| class='wikitable' \n|- \n| col1 || col2 \n|} End"
    cleaned, stats = clean_wikitext(raw)
    assert "wikitable" not in cleaned
    assert "col1" not in cleaned
    assert "Start End" in cleaned


def test_link_markup_resolution():
    # Piped link: [[Earth|our planet]] -> our planet
    # Simple link: [[Solar System]] -> Solar System
    raw = "Life on [[Earth|our planet]] in the [[Solar System]]."
    cleaned, _ = clean_wikitext(raw)
    assert cleaned == "Life on our planet in the Solar System."


def test_file_and_category_stripping():
    raw = "Article text [[File:Sun.jpg|thumb|The Sun]] [[Category:Stars]]."
    cleaned, _ = clean_wikitext(raw)
    assert "File:" not in cleaned
    assert "Category:" not in cleaned
    assert "Sun.jpg" not in cleaned
    assert cleaned == "Article text."


def test_bold_italic_quotes():
    raw = "'''Bold Text''' and ''Italic Text'' and '''''Both'''''."
    cleaned, _ = clean_wikitext(raw)
    assert "'''" not in cleaned
    assert "''" not in cleaned
    assert cleaned == "Bold Text and Italic Text and Both."
