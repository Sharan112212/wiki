package com.team.wikisearch.util

import com.team.wikisearch.data.model.SearchMode

data class ProcessedQuery(
    val cleanQuery: String,
    val mode: SearchMode,
    val isAutoSwitchedToPhrase: Boolean
)

object QueryUtils {
    /**
     * Processes user search input.
     * If the query starts and ends with double quotes (e.g., '"albert einstein"'),
     * it auto-switches to PHRASE mode and strips the double quotes before returning.
     */
    fun processQuery(rawQuery: String, currentMode: SearchMode): ProcessedQuery {
        val trimmed = rawQuery.trim()
        if (trimmed.length >= 2 && trimmed.startsWith("\"") && trimmed.endsWith("\"")) {
            val stripped = trimmed.substring(1, trimmed.length - 1).trim()
            return ProcessedQuery(
                cleanQuery = stripped,
                mode = SearchMode.PHRASE,
                isAutoSwitchedToPhrase = (currentMode != SearchMode.PHRASE)
            )
        }
        return ProcessedQuery(
            cleanQuery = trimmed,
            mode = currentMode,
            isAutoSwitchedToPhrase = false
        )
    }
}
