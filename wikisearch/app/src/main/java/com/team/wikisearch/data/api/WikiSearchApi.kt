package com.team.wikisearch.data.api

import com.team.wikisearch.data.model.ArticleResponse
import com.team.wikisearch.data.model.SearchResponse
import com.team.wikisearch.data.model.StatsResponse
import retrofit2.http.GET
import retrofit2.http.Path
import retrofit2.http.Query

interface WikiSearchApi {

    @GET("search")
    suspend fun search(
        @Query("q") query: String,
        @Query("mode") mode: String,
        @Query("k") k: Int
    ): SearchResponse

    @GET("article/{id}")
    suspend fun getArticle(
        @Path("id") id: Long
    ): ArticleResponse

    @GET("stats")
    suspend fun getStats(): StatsResponse
}
