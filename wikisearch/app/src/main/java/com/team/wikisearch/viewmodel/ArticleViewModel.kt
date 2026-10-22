package com.team.wikisearch.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.team.wikisearch.data.datastore.SettingsDataStore
import com.team.wikisearch.data.model.ArticleResponse
import com.team.wikisearch.data.repository.WikiSearchRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

sealed class ArticleUiState {
    data object Loading : ArticleUiState()
    data class Success(val article: ArticleResponse, val highlightQuery: String) : ArticleUiState()
    data class Error(val message: String) : ArticleUiState()
}

class ArticleViewModel(
    private val repository: WikiSearchRepository,
    private val settingsDataStore: SettingsDataStore
) : ViewModel() {

    private val _uiState = MutableStateFlow<ArticleUiState>(ArticleUiState.Loading)
    val uiState: StateFlow<ArticleUiState> = _uiState.asStateFlow()

    private val _fontSizeSp = MutableStateFlow(16)
    val fontSizeSp: StateFlow<Int> = _fontSizeSp.asStateFlow()

    private var currentArticleId: Long = -1L
    private var currentQuery: String = ""

    fun loadArticle(articleId: Long, query: String) {
        currentArticleId = articleId
        currentQuery = query

        viewModelScope.launch {
            _uiState.value = ArticleUiState.Loading
            val baseUrl = settingsDataStore.serverUrl.first()

            val result = repository.getArticle(baseUrl, articleId)
            result.fold(
                onSuccess = { article ->
                    _uiState.value = ArticleUiState.Success(article, query)
                },
                onFailure = { throwable ->
                    _uiState.value = ArticleUiState.Error(
                        throwable.localizedMessage ?: "Unable to load article content."
                    )
                }
            )
        }
    }

    fun retry() {
        if (currentArticleId != -1L) {
            loadArticle(currentArticleId, currentQuery)
        }
    }

    fun increaseFontSize() {
        if (_fontSizeSp.value < 28) {
            _fontSizeSp.value += 2
        }
    }

    fun decreaseFontSize() {
        if (_fontSizeSp.value > 12) {
            _fontSizeSp.value -= 2
        }
    }
}
