package com.team.wikisearch.ui.navigation

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Analytics
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.team.wikisearch.ui.screens.ArticleScreen
import com.team.wikisearch.ui.screens.SearchScreen
import com.team.wikisearch.ui.screens.SettingsScreen
import com.team.wikisearch.ui.screens.StatsScreen
import com.team.wikisearch.viewmodel.ArticleViewModel
import com.team.wikisearch.viewmodel.SearchViewModel
import com.team.wikisearch.viewmodel.SettingsViewModel
import com.team.wikisearch.viewmodel.StatsViewModel

sealed class Screen(val route: String, val title: String) {
    data object Search : Screen("search", "Search")
    data object Stats : Screen("stats", "Stats")
    data object Settings : Screen("settings", "Settings")
}

@Composable
fun WikiSearchAppNav(
    searchViewModel: SearchViewModel,
    articleViewModel: ArticleViewModel,
    settingsViewModel: SettingsViewModel,
    statsViewModel: StatsViewModel
) {
    val navController = rememberNavController()
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = navBackStackEntry?.destination?.route

    val bottomNavItems = listOf(
        Screen.Search,
        Screen.Stats,
        Screen.Settings
    )

    val showBottomBar = currentRoute in bottomNavItems.map { it.route }

    Scaffold(
        bottomBar = {
            if (showBottomBar) {
                NavigationBar {
                    bottomNavItems.forEach { screen ->
                        NavigationBarItem(
                            selected = currentRoute == screen.route,
                            onClick = {
                                navController.navigate(screen.route) {
                                    popUpTo(navController.graph.findStartDestination().id) {
                                        saveState = true
                                    }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            },
                            icon = {
                                when (screen) {
                                    Screen.Search -> Icon(Icons.Default.Search, contentDescription = "Search")
                                    Screen.Stats -> Icon(Icons.Default.Analytics, contentDescription = "Stats")
                                    Screen.Settings -> Icon(Icons.Default.Settings, contentDescription = "Settings")
                                }
                            },
                            label = { Text(screen.title) }
                        )
                    }
                }
            }
        }
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = Screen.Search.route,
            modifier = Modifier.padding(innerPadding)
        ) {
            composable(Screen.Search.route) {
                SearchScreen(
                    viewModel = searchViewModel,
                    onArticleClick = { articleId, query ->
                        val encodedQuery = Uri.encode(query.ifBlank { " " })
                        navController.navigate("article/$articleId/$encodedQuery")
                    }
                )
            }

            composable(
                route = "article/{articleId}/{query}",
                arguments = listOf(
                    navArgument("articleId") { type = NavType.LongType },
                    navArgument("query") { type = NavType.StringType }
                )
            ) { backStackEntry ->
                val articleId = backStackEntry.arguments?.getLong("articleId") ?: -1L
                val query = backStackEntry.arguments?.getString("query") ?: ""

                ArticleScreen(
                    articleId = articleId,
                    query = Uri.decode(query).trim(),
                    viewModel = articleViewModel,
                    onBackClick = { navController.popBackStack() }
                )
            }

            composable(Screen.Stats.route) {
                StatsScreen(
                    statsViewModel = statsViewModel,
                    searchViewModel = searchViewModel
                )
            }

            composable(Screen.Settings.route) {
                SettingsScreen(viewModel = settingsViewModel)
            }
        }
    }
}
