package com.team.wikisearch.data.model

import com.google.gson.annotations.SerializedName

enum class SearchMode(val value: String) {
    KEYWORD("keyword"),
    PHRASE("phrase");

    companion object {
        fun fromValue(value: String): SearchMode =
            entries.find { it.value.equals(value, ignoreCase = true) } ?: KEYWORD
    }
}

data class SearchResult(
    @SerializedName("id") val id: Long,
    @SerializedName("title") val title: String,
    @SerializedName("score") val score: Double,
    @SerializedName("snippet") val snippet: String
)

data class SearchResponse(
    @SerializedName("took_ms") val tookMs: Double,
    @SerializedName("total") val total: Int,
    @SerializedName("results") val results: List<SearchResult>
)

data class ArticleResponse(
    @SerializedName("id") val id: Long,
    @SerializedName("title") val title: String,
    @SerializedName("text") val text: String
)

data class StatsResponse(
    @SerializedName("doc_count") val docCount: Long,
    @SerializedName("build_time_s") val buildTimeS: Double,
    @SerializedName("index_size_mb") val indexSizeMb: Double,
    @SerializedName("corpus_size_mb") val corpusSizeMb: Double,
    @SerializedName("ratio") val ratio: Double,
    @SerializedName("compressed") val compressed: Boolean
)
