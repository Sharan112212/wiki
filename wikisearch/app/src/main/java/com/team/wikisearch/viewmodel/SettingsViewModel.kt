package com.team.wikisearch.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.team.wikisearch.data.datastore.SettingsDataStore
import com.team.wikisearch.data.repository.WikiSearchRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

sealed class TestConnectionState {
    data object Idle : TestConnectionState()
    data object Testing : TestConnectionState()
    data class Success(val message: String, val latencyMs: Long) : TestConnectionState()
    data class Error(val message: String) : TestConnectionState()
}

class SettingsViewModel(
    private val repository: WikiSearchRepository,
    private val settingsDataStore: SettingsDataStore
) : ViewModel() {

    val serverUrl: StateFlow<String> = MutableStateFlow(SettingsDataStore.DEFAULT_SERVER_URL)
    val resultsK: StateFlow<Int> = MutableStateFlow(SettingsDataStore.DEFAULT_K)
    val theme: StateFlow<String> = MutableStateFlow(SettingsDataStore.DEFAULT_THEME)

    private val _testConnectionState = MutableStateFlow<TestConnectionState>(TestConnectionState.Idle)
    val testConnectionState: StateFlow<TestConnectionState> = _testConnectionState.asStateFlow()

    init {
        viewModelScope.launch {
            settingsDataStore.serverUrl.collect {
                (serverUrl as MutableStateFlow).value = it
            }
        }
        viewModelScope.launch {
            settingsDataStore.resultsK.collect {
                (resultsK as MutableStateFlow).value = it
            }
        }
        viewModelScope.launch {
            settingsDataStore.theme.collect {
                (theme as MutableStateFlow).value = it
            }
        }
    }

    fun updateServerUrl(newUrl: String) {
        viewModelScope.launch {
            settingsDataStore.setServerUrl(newUrl)
            _testConnectionState.value = TestConnectionState.Idle
        }
    }

    fun updateResultsK(k: Int) {
        viewModelScope.launch {
            settingsDataStore.setResultsK(k)
        }
    }

    fun updateTheme(themeStr: String) {
        viewModelScope.launch {
            settingsDataStore.setTheme(themeStr)
        }
    }

    fun testConnection() {
        viewModelScope.launch {
            _testConnectionState.value = TestConnectionState.Testing
            val currentUrl = settingsDataStore.serverUrl.first()

            val result = repository.getStats(currentUrl)
            result.fold(
                onSuccess = { (stats, latencyMs) ->
                    _testConnectionState.value = TestConnectionState.Success(
                        message = "Connected! Index contains ${stats.docCount} documents.",
                        latencyMs = latencyMs
                    )
                },
                onFailure = { throwable ->
                    _testConnectionState.value = TestConnectionState.Error(
                        throwable.localizedMessage ?: "Failed to connect to backend at $currentUrl"
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
