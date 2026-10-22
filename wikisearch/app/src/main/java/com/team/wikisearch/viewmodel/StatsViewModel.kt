package com.team.wikisearch.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.team.wikisearch.data.datastore.SettingsDataStore
import com.team.wikisearch.data.model.StatsResponse
import com.team.wikisearch.data.repository.WikiSearchRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

sealed class StatsUiState {
    data object Loading : StatsUiState()
    data class Success(
        val stats: StatsResponse,
        val e2eLatencyMs: Long
    ) : StatsUiState()
    data class Error(val message: String) : StatsUiState()
}

class StatsViewModel(
    private val repository: WikiSearchRepository,
    private val settingsDataStore: SettingsDataStore
) : ViewModel() {

    private val _uiState = MutableStateFlow<StatsUiState>(StatsUiState.Loading)
    val uiState: StateFlow<StatsUiState> = _uiState.asStateFlow()

    fun loadStats() {
        viewModelScope.launch {
            _uiState.value = StatsUiState.Loading
            val baseUrl = settingsDataStore.serverUrl.first()

            val result = repository.getStats(baseUrl)
            result.fold(
                onSuccess = { (stats, latencyMs) ->
                    _uiState.value = StatsUiState.Success(
                        stats = stats,
                        e2eLatencyMs = latencyMs
                    )
                },
                onFailure = { throwable ->
                    _uiState.value = StatsUiState.Error(
                        throwable.localizedMessage ?: "Failed to fetch index statistics."
                    )
                }
            )
        }
    }
}
