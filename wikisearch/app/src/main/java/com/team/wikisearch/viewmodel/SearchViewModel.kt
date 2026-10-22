package com.team.wikisearch.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.team.wikisearch.data.datastore.SettingsDataStore
import com.team.wikisearch.data.model.SearchMode
import com.team.wikisearch.data.model.SearchResult
import com.team.wikisearch.data.repository.WikiSearchRepository
import com.team.wikisearch.util.QueryUtils
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

sealed class SearchUiState {
    data object Idle : SearchUiState()
    data object Loading : SearchUiState()
    data class Success(
        val results: List<SearchResult>,
        val total: Int,
        val tookMs: Double,
        val e2eLatencyMs: Long,
        val cleanQuery: String,
        val searchMode: SearchMode
    ) : SearchUiState()
    data object Empty : SearchUiState()
    data class Error(val message: String) : SearchUiState()
}

class SearchViewModel(
    private val repository: WikiSearchRepository,
    private val settingsDataStore: SettingsDataStore
) : ViewModel() {

    private val _uiState = MutableStateFlow<SearchUiState>(SearchUiState.Idle)
    val uiState: StateFlow<SearchUiState> = _uiState.asStateFlow()

    private val _rawQuery = MutableStateFlow("")
    val rawQuery: StateFlow<String> = _rawQuery.asStateFlow()

    private val _selectedMode = MutableStateFlow(SearchMode.KEYWORD)
    val selectedMode: StateFlow<SearchMode> = _selectedMode.asStateFlow()

    private val _autoSwitchedNotice = MutableStateFlow<String?>(null)
    val autoSwitchedNotice: StateFlow<String?> = _autoSwitchedNotice.asStateFlow()

    private var activeSearchJob: Job? = null

    val searchHistory: StateFlow<List<String>> = MutableStateFlow(emptyList())

    init {
        viewModelScope.launch {
            settingsDataStore.searchHistory.collect { historyList ->
                (searchHistory as MutableStateFlow).value = historyList
            }
        }
    }

    fun onQueryChanged(newQuery: String) {
        _rawQuery.value = newQuery
        if (newQuery.isBlank() && _uiState.value !is SearchUiState.Idle) {
            _uiState.value = SearchUiState.Idle
            _autoSwitchedNotice.value = null
        }
    }

    fun onModeSelected(mode: SearchMode) {
        _selectedMode.value = mode
        if (_rawQuery.value.isNotBlank()) {
            performSearch()
        }
    }

    fun clearQuery() {
        _rawQuery.value = ""
        _uiState.value = SearchUiState.Idle
        _autoSwitchedNotice.value = null
    }

    fun dismissAutoSwitchNotice() {
        _autoSwitchedNotice.value = null
    }

    fun performSearch(queryToRun: String? = null) {
        val queryInput = queryToRun ?: _rawQuery.value
        if (queryInput.isBlank()) return

        if (queryToRun != null) {
            _rawQuery.value = queryToRun
        }

        val processed = QueryUtils.processQuery(queryInput, _selectedMode.value)
        _selectedMode.value = processed.mode

        if (processed.isAutoSwitchedToPhrase) {
            _autoSwitchedNotice.value = "Quoted query detected: switched to Phrase mode"
        } else {
            _autoSwitchedNotice.value = null
        }

        // Cancel previous pending search request
        activeSearchJob?.cancel()

        activeSearchJob = viewModelScope.launch {
            _uiState.value = SearchUiState.Loading

            // Save to DataStore search history
            settingsDataStore.addSearchHistory(processed.cleanQuery)

            val baseUrl = settingsDataStore.serverUrl.first()
            val k = settingsDataStore.resultsK.first()

            val result = repository.search(
                baseUrl = baseUrl,
                query = processed.cleanQuery,
                mode = processed.mode.value,
                k = k
            )

            result.fold(
                onSuccess = { searchData ->
                    if (searchData.response.results.isEmpty()) {
                        _uiState.value = SearchUiState.Empty
                    } else {
                        _uiState.value = SearchUiState.Success(
                            results = searchData.response.results,
                            total = searchData.response.total,
                            tookMs = searchData.response.tookMs,
                            e2eLatencyMs = searchData.e2eLatencyMs,
                            cleanQuery = processed.cleanQuery,
                            searchMode = processed.mode
                        )
                    }
                },
                onFailure = { throwable ->
                    _uiState.value = SearchUiState.Error(
                        throwable.localizedMessage ?: "Failed to connect to backend search engine."
                    )
                }
            )
        }
    }

    fun clearSearchHistory() {
        viewModelScope.launch {
            settingsDataStore.clearSearchHistory()
        }
    }
}
