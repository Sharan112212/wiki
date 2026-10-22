package com.team.wikisearch.ui.screens

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.team.wikisearch.data.model.SearchMode
import com.team.wikisearch.ui.components.EmptyStateView
import com.team.wikisearch.ui.components.ErrorStateView
import com.team.wikisearch.ui.components.IdleStateView
import com.team.wikisearch.ui.components.LoadingStateView
import com.team.wikisearch.ui.components.ResultCard
import com.team.wikisearch.ui.components.SearchHeaderBar
import com.team.wikisearch.viewmodel.SearchUiState
import com.team.wikisearch.viewmodel.SearchViewModel

@Composable
fun SearchScreen(
    viewModel: SearchViewModel,
    onArticleClick: (articleId: Long, query: String) -> Unit,
    modifier: Modifier = Modifier
) {
    val uiState by viewModel.uiState.collectAsState()
    val rawQuery by viewModel.rawQuery.collectAsState()
    val selectedMode by viewModel.selectedMode.collectAsState()
    val autoSwitchNotice by viewModel.autoSwitchedNotice.collectAsState()
    val searchHistory by viewModel.searchHistory.collectAsState()

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        SearchHeaderBar(
            query = rawQuery,
            onQueryChange = viewModel::onQueryChanged,
            onSearchSubmit = { viewModel.performSearch() },
            onClearQuery = viewModel::clearQuery,
            selectedMode = selectedMode,
            onModeSelect = viewModel::onModeSelected,
            autoSwitchNotice = autoSwitchNotice,
            onDismissNotice = viewModel::dismissAutoSwitchNotice
        )

        when (val state = uiState) {
            is SearchUiState.Idle -> {
                IdleStateView(
                    recentSearches = searchHistory,
                    onQueryClick = { sampleQuery ->
                        viewModel.performSearch(sampleQuery)
                    },
                    onClearHistory = viewModel::clearSearchHistory
                )
            }

            is SearchUiState.Loading -> {
                LoadingStateView()
            }

            is SearchUiState.Success -> {
                Column(modifier = Modifier.fillMaxSize()) {
                    // Header card showing "{total} results in {took_ms} ms"
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(bottom = 12.dp),
                        shape = RoundedCornerShape(12.dp),
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.surfaceVariant
                        )
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 16.dp, vertical = 10.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = "${state.total} results found",
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = FontWeight.SemiBold,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )

                            Surface(
                                shape = RoundedCornerShape(8.dp),
                                color = MaterialTheme.colorScheme.primaryContainer
                            ) {
                                Text(
                                    text = "Server: ${state.tookMs} ms | E2E: ${state.e2eLatencyMs} ms",
                                    style = MaterialTheme.typography.labelSmall,
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.onPrimaryContainer,
                                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                                )
                            }
                        }
                    }

                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        verticalArrangement = Arrangement.spacedBy(10.dp),
                        contentPadding = PaddingValues(bottom = 16.dp)
                    ) {
                        itemsIndexed(
                            items = state.results,
                            key = { _, item -> item.id }
                        ) { index, result ->
                            ResultCard(
                                rank = index + 1,
                                result = result,
                                onClick = { onArticleClick(result.id, state.cleanQuery) }
                            )
                        }
                    }
                }
            }

            is SearchUiState.Empty -> {
                EmptyStateView(
                    query = rawQuery,
                    onTryPhraseMode = {
                        val newMode = if (selectedMode == SearchMode.KEYWORD) SearchMode.PHRASE else SearchMode.KEYWORD
                        viewModel.onModeSelected(newMode)
                    }
                )
            }

            is SearchUiState.Error -> {
                ErrorStateView(
                    message = state.message,
                    onRetry = { viewModel.performSearch() }
                )
            }
        }
    }
}
