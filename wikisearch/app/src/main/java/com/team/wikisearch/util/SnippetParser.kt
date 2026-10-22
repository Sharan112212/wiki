package com.team.wikisearch.util

import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle

object SnippetParser {
    /**
     * Parses a snippet string containing `<b>...</b>` tags into a Jetpack Compose [AnnotatedString].
     * Highlights matches with bold weight and a warm subtle background color.
     */
    fun parseSnippetToAnnotatedString(
        snippetHtml: String,
        highlightBgColor: Color = Color(0x33FFB74D), // Soft amber/warm accent
        highlightTextColor: Color = Color.Unspecified
    ): AnnotatedString {
        if (snippetHtml.isEmpty()) return AnnotatedString("")

        return buildAnnotatedString {
            var currentIndex = 0
            val regex = Regex("(?i)<b>(.*?)</b>")
            val matches = regex.findAll(snippetHtml)

            for (match in matches) {
                val start = match.range.first
                val end = match.range.last + 1

                // Append unhighlighted preceding text
                if (start > currentIndex) {
                    append(snippetHtml.substring(currentIndex, start))
                }

                // Append highlighted bold match text (inner match group 1)
                val matchedText = match.groupValues[1]
                withStyle(
                    SpanStyle(
                        fontWeight = FontWeight.Bold,
                        background = highlightBgColor,
                        color = highlightTextColor
                    )
                ) {
                    append(matchedText)
                }

                currentIndex = end
            }

            // Append remaining trailing text
            if (currentIndex < snippetHtml.length) {
                append(snippetHtml.substring(currentIndex))
            }
        }
    }
}
