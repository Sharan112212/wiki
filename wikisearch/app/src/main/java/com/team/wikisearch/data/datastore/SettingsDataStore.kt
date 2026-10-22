package com.team.wikisearch.data.datastore

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.core.stringSetPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "wikisearch_settings")

class SettingsDataStore(private val context: Context) {

    companion object {
        val SERVER_URL_KEY = stringPreferencesKey("server_url")
        val RESULTS_K_KEY = intPreferencesKey("results_k")
        val THEME_KEY = stringPreferencesKey("app_theme")
        val SEARCH_HISTORY_KEY = stringPreferencesKey("search_history_csv")

        const val DEFAULT_SERVER_URL = "http://10.0.2.2:8000/"
        const val DEFAULT_K = 10
        const val DEFAULT_THEME = "SYSTEM"
    }

    val serverUrl: Flow<String> = context.dataStore.data.map { preferences ->
        preferences[SERVER_URL_KEY] ?: DEFAULT_SERVER_URL
    }

    val resultsK: Flow<Int> = context.dataStore.data.map { preferences ->
        preferences[RESULTS_K_KEY] ?: DEFAULT_K
    }

    val theme: Flow<String> = context.dataStore.data.map { preferences ->
        preferences[THEME_KEY] ?: DEFAULT_THEME
    }

    val searchHistory: Flow<List<String>> = context.dataStore.data.map { preferences ->
        val raw = preferences[SEARCH_HISTORY_KEY] ?: ""
        if (raw.isBlank()) emptyList() else raw.split("\u001F").filter { it.isNotBlank() }
    }

    suspend fun setServerUrl(url: String) {
        val cleanUrl = if (url.trim().endsWith("/")) url.trim() else "${url.trim()}/"
        context.dataStore.edit { preferences ->
            preferences[SERVER_URL_KEY] = cleanUrl
        }
    }

    suspend fun setResultsK(k: Int) {
        context.dataStore.edit { preferences ->
            preferences[RESULTS_K_KEY] = k
        }
    }

    suspend fun setTheme(themeStr: String) {
        context.dataStore.edit { preferences ->
            preferences[THEME_KEY] = themeStr
        }
    }

    suspend fun addSearchHistory(query: String) {
        val trimmed = query.trim()
        if (trimmed.isEmpty()) return
        context.dataStore.edit { preferences ->
            val currentRaw = preferences[SEARCH_HISTORY_KEY] ?: ""
            val currentList = if (currentRaw.isBlank()) emptyList() else currentRaw.split("\u001F")
            val newList = (listOf(trimmed) + currentList.filter { !it.equals(trimmed, ignoreCase = true) }).take(10)
            preferences[SEARCH_HISTORY_KEY] = newList.joinToString("\u001F")
        }
    }

    suspend fun clearSearchHistory() {
        context.dataStore.edit { preferences ->
            preferences[SEARCH_HISTORY_KEY] = ""
        }
    }
}
