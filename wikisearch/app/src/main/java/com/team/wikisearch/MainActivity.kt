package com.team.wikisearch

import android.app.Application
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import com.team.wikisearch.data.datastore.SettingsDataStore
import com.team.wikisearch.data.repository.WikiSearchRepository
import com.team.wikisearch.ui.navigation.WikiSearchAppNav
import com.team.wikisearch.ui.theme.WikiSearchTheme
import com.team.wikisearch.viewmodel.ArticleViewModel
import com.team.wikisearch.viewmodel.SearchViewModel
import com.team.wikisearch.viewmodel.SettingsViewModel
import com.team.wikisearch.viewmodel.StatsViewModel

class WikiSearchApp : Application() {
    lateinit var repository: WikiSearchRepository
    lateinit var settingsDataStore: SettingsDataStore

    override fun onCreate() {
        super.onCreate()
        repository = WikiSearchRepository()
        settingsDataStore = SettingsDataStore(this)
    }
}

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()
        super.onCreate()
        enableEdgeToEdge()

        val app = application as WikiSearchApp
        val searchViewModel = SearchViewModel(app.repository, app.settingsDataStore)
        val articleViewModel = ArticleViewModel(app.repository, app.settingsDataStore)
        val settingsViewModel = SettingsViewModel(app.repository, app.settingsDataStore)
        val statsViewModel = StatsViewModel(app.repository, app.settingsDataStore)

        setContent {
            val themePreference by settingsViewModel.theme.collectAsState()
            val useDarkTheme = when (themePreference.uppercase()) {
                "DARK" -> true
                "LIGHT" -> false
                else -> isSystemInDarkTheme()
            }

            WikiSearchTheme(darkTheme = useDarkTheme) {
                WikiSearchAppNav(
                    searchViewModel = searchViewModel,
                    articleViewModel = articleViewModel,
                    settingsViewModel = settingsViewModel,
                    statsViewModel = statsViewModel
                )
            }
        }
    }
}
