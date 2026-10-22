package com.team.wikisearch

import com.team.wikisearch.data.model.SearchMode
import com.team.wikisearch.util.QueryUtils
import com.team.wikisearch.util.SnippetParser
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class QueryUtilsTest {

    @Test
    fun testNormalQueryInKeywordMode() {
        val result = QueryUtils.processQuery("solar eclipse", SearchMode.KEYWORD)
        assertEquals("solar eclipse", result.cleanQuery)
        assertEquals(SearchMode.KEYWORD, result.mode)
        assertFalse(result.isAutoSwitchedToPhrase)
    }

    @Test
    fun testQuotedQueryAutoSwitchesToPhraseMode() {
        val result = QueryUtils.processQuery("\"albert einstein\"", SearchMode.KEYWORD)
        assertEquals("albert einstein", result.cleanQuery)
        assertEquals(SearchMode.PHRASE, result.mode)
        assertTrue(result.isAutoSwitchedToPhrase)
    }

    @Test
    fun testQuotedQueryAlreadyInPhraseMode() {
        val result = QueryUtils.processQuery("\"quantum computing\"", SearchMode.PHRASE)
        assertEquals("quantum computing", result.cleanQuery)
        assertEquals(SearchMode.PHRASE, result.mode)
        assertFalse(result.isAutoSwitchedToPhrase)
    }
}

class SnippetParserTest {

    @Test
    fun testSnippetParsingStripsBAndPreservesText() {
        val rawSnippet = "A solar <b>eclipse</b> occurs when..."
        val annotated = SnippetParser.parseSnippetToAnnotatedString(rawSnippet)
        assertEquals("A solar eclipse occurs when...", annotated.text)
    }

    @Test
    fun testSnippetParsingMultipleMatches() {
        val rawSnippet = "<b>Albert</b> <b>Einstein</b> developed relativity."
        val annotated = SnippetParser.parseSnippetToAnnotatedString(rawSnippet)
        assertEquals("Albert Einstein developed relativity.", annotated.text)
    }
}
