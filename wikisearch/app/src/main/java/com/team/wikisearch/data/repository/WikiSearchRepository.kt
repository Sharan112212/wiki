package com.team.wikisearch.data.repository

import com.team.wikisearch.data.api.RetrofitClient
import com.team.wikisearch.data.model.ArticleResponse
import com.team.wikisearch.data.model.SearchResponse
import com.team.wikisearch.data.model.StatsResponse
import java.io.IOException
import java.net.SocketTimeoutException

data class SearchResultWithLatency(
    val response: SearchResponse,
    val e2eLatencyMs: Long
)

class WikiSearchRepository {

    suspend fun search(
        baseUrl: String,
        query: String,
        mode: String,
        k: Int
    ): Result<SearchResultWithLatency> {
        return try {
            val api = RetrofitClient.getApi(baseUrl)
            val startTime = System.currentTimeMillis()
            val response = api.search(query = query, mode = mode, k = k)
            val endTime = System.currentTimeMillis()
            val e2eLatency = endTime - startTime
            Result.success(SearchResultWithLatency(response, e2eLatency))
        } catch (e: SocketTimeoutException) {
            Result.failure(Exception("Connection timed out. Please check if the server at '$baseUrl' is running."))
        } catch (e: IOException) {
            Result.failure(Exception("Server unreachable. Verify server address ($baseUrl) and Wi-Fi connection."))
        } catch (e: Exception) {
            Result.failure(Exception("Search failed: ${e.localizedMessage ?: "Unknown network error"}"))
        }
    }

    suspend fun getArticle(
        baseUrl: String,
        id: Long
    ): Result<ArticleResponse> {
        return try {
            val api = RetrofitClient.getApi(baseUrl)
            val article = api.getArticle(id)
            Result.success(article)
        } catch (e: SocketTimeoutException) {
            Result.failure(Exception("Article request timed out."))
        } catch (e: IOException) {
            Result.failure(Exception("Server unreachable while loading article."))
        } catch (e: Exception) {
            Result.failure(Exception("Failed to load article: ${e.localizedMessage}"))
        }
    }

    suspend fun getStats(
        baseUrl: String
    ): Result<Pair<StatsResponse, Long>> {
        return try {
            val api = RetrofitClient.getApi(baseUrl)
            val startTime = System.currentTimeMillis()
            val stats = api.getStats()
            val e2eLatency = System.currentTimeMillis() - startTime
            Result.success(Pair(stats, e2eLatency))
        } catch (e: SocketTimeoutException) {
            Result.failure(Exception("Stats request timed out."))
        } catch (e: IOException) {
            Result.failure(Exception("Server unreachable at $baseUrl"))
        } catch (e: Exception) {
            Result.failure(Exception("Failed to fetch stats: ${e.localizedMessage}"))
        }
    }
}
