package com.team.wikisearch.util

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle

object ArticleHighlighter {
    /**
     * Highlights occurrences of query terms in full article text.
     */
    fun highlightQueryTerms(
        text: String,
        query: String,
        highlightBgColor: Color = Color(0x44FFB74D),
        highlightTextColor: Color = Color.Unspecified
    ): AnnotatedString {
        if (text.isEmpty() || query.isBlank()) return AnnotatedString(text)

        val terms = query.split("\\s+".toRegex())
            .map { it.replace(Regex("[^a-zA-Z0-9]"), "") }
            .filter { it.length >= 2 }

        if (terms.isEmpty()) return AnnotatedString(text)

        val pattern = terms.joinToString("|") { Regex.escape(it) }
        val regex = Regex("(?i)\\b($pattern)\\b")

        return buildAnnotatedString {
            var currentIndex = 0
            val matches = regex.findAll(text)

            for (match in matches) {
                val start = match.range.first
                val end = match.range.last + 1

                if (start > currentIndex) {
                    append(text.substring(currentIndex, start))
                }

                withStyle(
                    SpanStyle(
                        fontWeight = FontWeight.SemiBold,
                        background = highlightBgColor,
                        color = highlightTextColor
                    )
                ) {
                    append(text.substring(start, end))
                }

                currentIndex = end
            }

            if (currentIndex < text.length) {
                append(text.substring(currentIndex))
            }
        }
    }
}
