import React, { useState, useEffect } from 'react';
import {
  Search,
  X,
  Info,
  RotateCcw,
  Settings as SettingsIcon,
  BarChart3,
  BookOpen,
  Share2,
  Minus,
  Plus,
  CheckCircle2,
  AlertTriangle,
  Moon,
  Sun,
  Trash2,
  ExternalLink,
  Sparkles,
  Smartphone
} from 'lucide-react';

// Mock Articles matching backend contract
interface Article {
  id: number;
  title: string;
  text: string;
}

const MOCK_ARTICLES: Record<number, Article> = {
  12: {
    id: 12,
    title: 'Solar eclipse',
    text: `A solar eclipse occurs when the Moon passes between Earth and the Sun, thereby totally or partly obscuring the image of the Sun for a viewer on Earth. A total solar eclipse occurs when the Moon's apparent diameter is larger than the Sun's, blocking all direct sunlight, turning day into darkness. Total eclipses occur in a narrow path across Earth's surface, with the partial solar eclipse visible over a surrounding region thousands of kilometres wide. During a total solar eclipse, the solar corona is clearly visible to the naked eye.

Eclipses have fascinated humanity for millennia. Ancient astronomers learned to predict eclipses by observing the Saros cycle of orbital alignments.`
  },
  42: {
    id: 42,
    title: 'Albert Einstein',
    text: `Albert Einstein (14 March 1879 – 18 April 1955) was a German-born theoretical physicist who is widely held to be one of the greatest and most influential scientists of all time. Best known for developing the theory of relativity, Einstein also made important contributions to quantum mechanics, and was thus a central figure in the revolutionary reshaping of the scientific understanding of nature that modern physics accomplished in the first decades of the twentieth century.

His mass–energy equivalence formula E = mc², which arises from relativity theory, has been dubbed 'the world's most famous equation'. He received the 1921 Nobel Prize in Physics for his services to theoretical physics, and especially for his discovery of the law of the photoelectric effect.`
  },
  108: {
    id: 108,
    title: 'Quantum computing',
    text: `Quantum computing is a rapidly-emerging technology that harnesses the laws of quantum mechanics to solve problems too complex for classical computers. Today, IBM Quantum makes real quantum hardware available to thousands of developers.

While classical computers store information in binary bits (0s and 1s), quantum computing utilizes quantum bits or qubits. Qubits leverage superposition and quantum entanglement to evaluate massive solution spaces simultaneously.`
  },
  204: {
    id: 204,
    title: 'Black hole',
    text: `A black hole is a region of spacetime where gravity is so strong that nothing — no particles or even electromagnetic radiation such as light — can escape from it. The theory of general relativity predicts that a sufficiently compact mass can deform spacetime to form a black hole.

The boundary of no escape is called the event horizon. Although the event horizon has an enormous effect on the fate and circumstances of an object crossing it, according to general relativity it has no locally detectable features.`
  },
  512: {
    id: 512,
    title: 'World War II',
    text: `World War II or the Second World War was a global conflict that lasted from 1939 to 1945. The vast majority of the world's countries — including all of the great powers — fought as part of two opposing military alliances: the Allies and the Axis powers.`
  }
};

type SearchMode = 'keyword' | 'phrase';
type Tab = 'search' | 'stats' | 'settings';
type ThemeMode = 'system' | 'light' | 'dark';

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('search');
  const [query, setQuery] = useState('');
  const [searchMode, setSearchMode] = useState<SearchMode>('keyword');
  const [serverUrl, setServerUrl] = useState('http://localhost:8000/');
  const [resultsK, setResultsK] = useState(10);
  const [themeMode, setThemeMode] = useState<ThemeMode>('dark');
  const [searchHistory, setSearchHistory] = useState<string[]>([
    'solar eclipse',
    '"albert einstein"',
    'quantum computing'
  ]);

  // Search State
  const [isSearching, setIsSearching] = useState(false);
  const [searchSuccess, setSearchSuccess] = useState<{
    results: { id: number; title: string; score: number; snippet: string }[];
    total: number;
    tookMs: number;
    e2eMs: number;
    cleanQuery: string;
  } | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [autoSwitchNotice, setAutoSwitchNotice] = useState<string | null>(null);

  // Selected Article Reader State
  const [selectedArticleId, setSelectedArticleId] = useState<number | null>(null);
  const [loadedArticle, setLoadedArticle] = useState<{ id: number; title: string; text: string; length?: number } | null>(null);
  const [articleLoading, setArticleLoading] = useState(false);
  const [fontSizeSp, setFontSizeSp] = useState(16);

  // Stats & Connection State
  const [testingConn, setTestingConn] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string; latency?: number } | null>(null);
  const [statsData, setStatsData] = useState<any | null>(null);

  const isDark = themeMode === 'dark';

  // Automatically fetch stats on load
  useEffect(() => {
    handleTestConnection();
  }, []);

  const handleSearch = (customQuery?: string) => {
    const raw = customQuery !== undefined ? customQuery : query;
    if (!raw.trim()) return;

    if (customQuery !== undefined) {
      setQuery(customQuery);
    }

    let cleanQ = raw.trim();
    let modeToUse = searchMode;

    if (cleanQ.length >= 2 && cleanQ.startsWith('"') && cleanQ.endsWith('"')) {
      cleanQ = cleanQ.slice(1, -1).trim();
      modeToUse = 'phrase';
      setSearchMode('phrase');
      setAutoSwitchNotice('Quoted query detected: auto-switched to Phrase mode');
    } else {
      setAutoSwitchNotice(null);
    }

    setIsSearching(true);
    setSearchError(null);

    // Add to history
    setSearchHistory((prev) => Array.from(new Set([cleanQ, ...prev])).slice(0, 10));

    const start = performance.now();
    const baseUrl = serverUrl.endsWith('/') ? serverUrl : serverUrl + '/';
    
    fetch(`${baseUrl}search?q=${encodeURIComponent(cleanQ)}&mode=${modeToUse}&k=${resultsK}`)
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        return res.json();
      })
      .then((data) => {
        const e2eMs = Math.round(performance.now() - start);
        setIsSearching(false);
        setSearchSuccess({
          results: data.results || [],
          total: data.total ?? (data.results ? data.results.length : 0),
          tookMs: data.took_ms ?? 0,
          e2eMs,
          cleanQuery: cleanQ
        });
      })
      .catch((err) => {
        setIsSearching(false);
        setSearchError(`Failed to reach backend at ${serverUrl} (${err.message}). Check if backend is running.`);
      });
  };

  const openArticle = (id: number, fallbackTitle?: string) => {
    setSelectedArticleId(id);
    setArticleLoading(true);
    setLoadedArticle(null);

    const baseUrl = serverUrl.endsWith('/') ? serverUrl : serverUrl + '/';
    fetch(`${baseUrl}article/${id}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setLoadedArticle(data);
        setArticleLoading(false);
      })
      .catch(() => {
        const fallback = MOCK_ARTICLES[id] || { id, title: fallbackTitle || `Article ${id}`, text: 'Article text could not be loaded from server.' };
        setLoadedArticle(fallback);
        setArticleLoading(false);
      });
  };

  const handleTestConnection = () => {
    setTestingConn(true);
    setTestResult(null);
    const t0 = performance.now();
    const baseUrl = serverUrl.endsWith('/') ? serverUrl : serverUrl + '/';

    fetch(`${baseUrl}stats`)
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        return res.json();
      })
      .then((data) => {
        const lat = Math.round(performance.now() - t0);
        setTestingConn(false);
        setStatsData(data);
        const docs = data.num_docs ?? data.doc_count ?? 270509;
        const sizeHuman = data.index_size_human ?? `${data.index_size_mb || 830} MB`;
        setTestResult({
          success: true,
          message: `Connected! Index contains ${docs.toLocaleString()} documents (${sizeHuman}).`,
          latency: lat
        });
      })
      .catch((err) => {
        setTestingConn(false);
        setTestResult({
          success: false,
          message: `Connection failed to ${serverUrl}: ${err.message}.`,
        });
      });
  };

  const renderSnippetText = (htmlSnippet: string) => {
    const parts = htmlSnippet.split(/(<b>.*?<\/b>)/gi);
    return parts.map((part, i) => {
      if (part.toLowerCase().startsWith('<b>') && part.toLowerCase().endsWith('</b>')) {
        const clean = part.replace(/<\/?b>/gi, '');
        return (
          <span key={i} className="font-bold bg-amber-500/20 text-amber-300 dark:text-amber-200 px-1 rounded">
            {clean}
          </span>
        );
      }
      return part;
    });
  };

  const renderHighlightedArticleText = (text: string, highlightQuery: string) => {
    if (!highlightQuery) return text;
    const terms = highlightQuery
      .split(/\s+/)
      .map((t) => t.replace(/[^a-zA-Z0-9]/g, ''))
      .filter((t) => t.length >= 2);
    if (!terms.length) return text;

    const pattern = new RegExp(`\\b(${terms.join('|')})\\b`, 'gi');
    const parts = text.split(pattern);

    return parts.map((part, i) => {
      if (terms.some((t) => t.toLowerCase() === part.toLowerCase())) {
        return (
          <span key={i} className="font-semibold bg-amber-500/30 text-amber-200 px-1 rounded">
            {part}
          </span>
        );
      }
      return part;
    });
  };

  return (
    <div className={`min-h-screen ${isDark ? 'bg-slate-950 text-slate-100' : 'bg-slate-50 text-slate-900'} flex flex-col items-center justify-center p-2 sm:p-4 transition-colors`}>
      {/* Mobile Shell Frame */}
      <div className={`w-full max-w-md h-[860px] max-h-[92vh] ${isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'} rounded-[36px] border-4 shadow-2xl flex flex-col overflow-hidden relative`}>
        {/* Android Status Bar */}
        <div className={`px-6 pt-3 pb-2 flex justify-between items-center text-xs font-medium ${isDark ? 'text-slate-400' : 'text-slate-500'} select-none`}>
          <span>9:41</span>
          <div className="flex items-center space-x-2">
            <span>5G</span>
            <div className="w-4 h-2.5 border border-current rounded-sm relative flex items-center p-0.5">
              <div className="w-full h-full bg-current rounded-2xs"></div>
            </div>
          </div>
        </div>

        {/* Top Header */}
        <div className="px-5 py-3 border-b border-slate-800/50 flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-indigo-600 to-amber-500 flex items-center justify-center text-white shadow-md">
              <Search className="w-4 h-4" />
            </div>
            <div>
              <h1 className="font-bold text-base leading-tight tracking-tight">WikiSearch</h1>
              <p className="text-[10px] text-indigo-400 font-medium">BM25 Inverted Index</p>
            </div>
          </div>
          <button
            onClick={() => setThemeMode(isDark ? 'light' : 'dark')}
            className={`p-2 rounded-xl transition ${isDark ? 'bg-slate-800 text-amber-400 hover:bg-slate-700' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'}`}
          >
            {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>
        </div>

        {/* Article Reader Overlay View */}
        {selectedArticleId !== null && (
          <div className={`absolute inset-0 z-30 ${isDark ? 'bg-slate-900' : 'bg-white'} flex flex-col animate-in fade-in slide-in-from-bottom duration-200`}>
            {/* Top Bar */}
            <div className="p-4 border-b border-slate-800 flex items-center justify-between">
              <button
                onClick={() => setSelectedArticleId(null)}
                className="flex items-center space-x-1.5 text-sm font-medium text-indigo-400 hover:text-indigo-300"
              >
                <X className="w-5 h-5" />
                <span>Back</span>
              </button>
              <h2 className="text-sm font-bold truncate max-w-[180px]">
                {loadedArticle?.title || MOCK_ARTICLES[selectedArticleId]?.title || (articleLoading ? 'Loading...' : `Article #${selectedArticleId}`)}
              </h2>
              <button
                onClick={() => {
                  const t = loadedArticle?.title || MOCK_ARTICLES[selectedArticleId]?.title || '';
                  const txt = loadedArticle?.text || MOCK_ARTICLES[selectedArticleId]?.text || '';
                  if (navigator.share) {
                    navigator.share({ title: t, text: txt });
                  } else {
                    alert('Share triggered: ' + t);
                  }
                }}
                className="p-2 text-indigo-400 hover:text-indigo-300"
              >
                <Share2 className="w-4 h-4" />
              </button>
            </div>

            {/* Font Control Bar */}
            <div className={`px-4 py-2 border-b border-slate-800/60 flex items-center justify-between text-xs ${isDark ? 'bg-slate-950/50' : 'bg-slate-50'}`}>
              <span className="font-medium text-slate-400">Font Size: {fontSizeSp}sp</span>
              <div className="flex items-center space-x-2">
                <button
                  disabled={fontSizeSp <= 12}
                  onClick={() => setFontSizeSp((s) => Math.max(12, s - 2))}
                  className="px-2.5 py-1 rounded-lg bg-slate-800 text-slate-200 disabled:opacity-40 hover:bg-slate-700 font-bold"
                >
                  A-
                </button>
                <button
                  disabled={fontSizeSp >= 28}
                  onClick={() => setFontSizeSp((s) => Math.min(28, s + 2))}
                  className="px-2.5 py-1 rounded-lg bg-slate-800 text-slate-200 disabled:opacity-40 hover:bg-slate-700 font-bold"
                >
                  A+
                </button>
              </div>
            </div>

            {/* Scrollable Article Text */}
            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              {articleLoading ? (
                <div className="py-20 text-center space-y-3 animate-pulse">
                  <div className="h-6 bg-slate-700/50 rounded w-2/3 mx-auto"></div>
                  <div className="h-4 bg-slate-700/30 rounded w-full"></div>
                  <div className="h-4 bg-slate-700/30 rounded w-5/6 mx-auto"></div>
                  <p className="text-xs text-indigo-400 font-medium pt-4">Decompressing article from Zstandard text store...</p>
                </div>
              ) : (
                <>
                  <h1 className="text-2xl font-extrabold">
                    {loadedArticle?.title || MOCK_ARTICLES[selectedArticleId]?.title || `Article #${selectedArticleId}`}
                  </h1>
                  <div
                    className="leading-relaxed whitespace-pre-line"
                    style={{ fontSize: `${fontSizeSp}px`, lineHeight: `${fontSizeSp * 1.5}px` }}
                  >
                    {renderHighlightedArticleText(
                      loadedArticle?.text || MOCK_ARTICLES[selectedArticleId]?.text || '',
                      searchSuccess?.cleanQuery || ''
                    )}
                  </div>
                </>
              )}

              {/* Attribution */}
              <div className={`mt-8 p-4 rounded-2xl border ${isDark ? 'bg-slate-950 border-slate-800 text-slate-400' : 'bg-slate-50 border-slate-200 text-slate-600'} text-xs text-center space-y-1`}>
                <p>Text from Wikipedia, licensed CC BY-SA 4.0</p>
                <a
                  href="https://creativecommons.org/licenses/by-sa/4.0/"
                  target="_blank"
                  rel="noreferrer"
                  className="text-indigo-400 underline font-medium hover:text-indigo-300 inline-flex items-center gap-1"
                >
                  creativecommons.org/licenses/by-sa/4.0/ <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          </div>
        )}

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {activeTab === 'search' && (
            <div className="space-y-4">
              {/* Search Bar */}
              <div className="space-y-2">
                <div className="relative flex items-center">
                  <Search className="w-4 h-4 absolute left-3.5 text-slate-400 pointer-events-none" />
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                    placeholder='Search Wikipedia... (e.g. "solar eclipse")'
                    className={`w-full pl-10 pr-9 py-2.5 text-sm rounded-2xl border outline-none transition ${isDark ? 'bg-slate-800 border-slate-700 text-white focus:border-indigo-500' : 'bg-slate-100 border-slate-200 text-slate-900 focus:border-indigo-500'}`}
                  />
                  {query && (
                    <button
                      onClick={() => {
                        setQuery('');
                        setSearchSuccess(null);
                        setAutoSwitchNotice(null);
                      }}
                      className="absolute right-3 text-slate-400 hover:text-slate-200"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>

                {/* Mode Selector */}
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400 font-medium">Search Mode:</span>
                  <div className={`p-0.5 rounded-xl border flex ${isDark ? 'bg-slate-800 border-slate-700' : 'bg-slate-100 border-slate-200'}`}>
                    <button
                      onClick={() => setSearchMode('keyword')}
                      className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${searchMode === 'keyword' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'}`}
                    >
                      Keyword
                    </button>
                    <button
                      onClick={() => setSearchMode('phrase')}
                      className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${searchMode === 'phrase' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'}`}
                    >
                      Phrase
                    </button>
                  </div>
                </div>

                {/* Auto Switch Notice */}
                {autoSwitchNotice && (
                  <div className="p-2.5 rounded-xl bg-indigo-950/80 border border-indigo-700/60 text-indigo-200 text-xs flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <Info className="w-4 h-4 text-indigo-400 shrink-0" />
                      <span>{autoSwitchNotice}</span>
                    </div>
                    <button onClick={() => setAutoSwitchNotice(null)}>
                      <X className="w-3.5 h-3.5 text-indigo-300" />
                    </button>
                  </div>
                )}
              </div>

              {/* State 1: Searching Loading */}
              {isSearching && (
                <div className="space-y-3 py-2">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className={`p-4 rounded-2xl border ${isDark ? 'bg-slate-800/40 border-slate-800' : 'bg-slate-100 border-slate-200'} space-y-2 animate-pulse`}>
                      <div className="h-4 bg-slate-700/50 rounded w-1/2"></div>
                      <div className="h-3 bg-slate-700/30 rounded w-full"></div>
                      <div className="h-3 bg-slate-700/30 rounded w-4/5"></div>
                    </div>
                  ))}
                </div>
              )}

              {/* State 2: Idle State */}
              {!isSearching && !searchSuccess && (
                <div className="py-6 text-center space-y-5">
                  <div className="w-16 h-16 rounded-full bg-indigo-600/10 text-indigo-400 flex items-center justify-center mx-auto">
                    <BookOpen className="w-8 h-8" />
                  </div>
                  <div>
                    <h3 className="font-bold text-base">Search Wikipedia Inverted Index</h3>
                    <p className="text-xs text-slate-400 mt-1">BM25 keyword ranking or exact phrase search across local index</p>
                  </div>

                  <div className="space-y-2 text-left">
                    <p className="text-xs font-semibold text-indigo-400">Try Example Queries:</p>
                    <div className="flex flex-wrap gap-1.5">
                      {['solar eclipse', '"albert einstein"', 'quantum computing', 'black hole'].map((sample) => (
                        <button
                          key={sample}
                          onClick={() => handleSearch(sample)}
                          className={`px-3 py-1.5 rounded-xl border text-xs font-medium transition ${isDark ? 'bg-slate-800/80 border-slate-700 hover:border-indigo-500' : 'bg-slate-100 border-slate-200 hover:border-indigo-500'}`}
                        >
                          {sample}
                        </button>
                      ))}
                    </div>
                  </div>

                  {searchHistory.length > 0 && (
                    <div className="space-y-2 text-left pt-2">
                      <div className="flex justify-between items-center">
                        <p className="text-xs font-semibold text-indigo-400">Recent Searches:</p>
                        <button
                          onClick={() => setSearchHistory([])}
                          className="text-[10px] text-slate-500 hover:text-slate-300"
                        >
                          Clear All
                        </button>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {searchHistory.map((h) => (
                          <button
                            key={h}
                            onClick={() => handleSearch(h)}
                            className={`px-3 py-1.5 rounded-xl border text-xs text-slate-300 ${isDark ? 'bg-slate-900 border-slate-800' : 'bg-slate-50 border-slate-200'}`}
                          >
                            {h}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* State 3: Search Success */}
              {!isSearching && searchSuccess && (
                <div className="space-y-3">
                  {/* Results Summary Header */}
                  <div className={`px-3.5 py-2.5 rounded-xl border flex items-center justify-between text-xs ${isDark ? 'bg-slate-800/60 border-slate-700/60' : 'bg-slate-100 border-slate-200'}`}>
                    <span className="font-semibold text-slate-300">{searchSuccess.total} results found</span>
                    <span className="px-2 py-0.5 rounded-md bg-indigo-950 text-indigo-300 font-mono text-[10px] font-bold">
                      Server: {searchSuccess.tookMs} ms | E2E: {searchSuccess.e2eMs} ms
                    </span>
                  </div>

                  {/* Results List */}
                  {searchSuccess.results.length === 0 ? (
                    <div className="py-10 text-center space-y-3">
                      <AlertTriangle className="w-10 h-10 text-amber-500 mx-auto" />
                      <h4 className="font-bold text-sm">No results found for "{searchSuccess.cleanQuery}"</h4>
                      <p className="text-xs text-slate-400">Try checking typos or switching search mode.</p>
                    </div>
                  ) : (
                    searchSuccess.results.map((res, index) => (
                      <div
                        key={res.id}
                        onClick={() => openArticle(res.id, res.title)}
                        className={`p-4 rounded-2xl border cursor-pointer transition hover:border-indigo-500/80 ${isDark ? 'bg-slate-800/80 border-slate-700' : 'bg-white border-slate-200 shadow-sm'}`}
                      >
                        <div className="flex justify-between items-start mb-1.5">
                          <div className="flex items-center space-x-2">
                            <span className="text-xs font-bold px-2 py-0.5 rounded-md bg-indigo-500/20 text-indigo-300">
                              #{index + 1}
                            </span>
                            <h3 className="font-bold text-sm text-indigo-200 hover:text-indigo-100">{res.title}</h3>
                          </div>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 font-semibold">
                            BM25: {res.score}
                          </span>
                        </div>
                        <p className="text-xs text-slate-300 leading-relaxed line-clamp-3">
                          {renderSnippetText(res.snippet)}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          )}

          {/* Tab 2: Stats */}
          {activeTab === 'stats' && (
            <div className="space-y-4">
              <h2 className="text-lg font-extrabold tracking-tight">Engine Statistics</h2>

              {/* Latency Breakdown Card */}
              <div className={`p-4 rounded-2xl border ${isDark ? 'bg-indigo-950/40 border-indigo-800/60' : 'bg-indigo-50 border-indigo-200'} space-y-2`}>
                <h3 className="text-xs font-bold uppercase tracking-wider text-indigo-400">Latency Breakdown</h3>
                {searchSuccess ? (
                  <div className="space-y-1.5 text-xs">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Server Processing (BM25):</span>
                      <span className="font-bold text-indigo-300">{searchSuccess.tookMs} ms</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">End-to-End (App Round-Trip):</span>
                      <span className="font-bold text-indigo-300">{searchSuccess.e2eMs} ms</span>
                    </div>
                    <div className="flex justify-between border-t border-indigo-800/40 pt-1.5">
                      <span className="text-slate-400">Network Overhead:</span>
                      <span className="font-semibold text-slate-300">{Math.max(0, searchSuccess.e2eMs - searchSuccess.tookMs)} ms</span>
                    </div>
                  </div>
                ) : (
                  <p className="text-xs text-slate-400">Run a search query to inspect real-time latency measurements.</p>
                )}
              </div>

              {/* Inverted Index Metrics Card */}
              <div className={`p-4 rounded-2xl border ${isDark ? 'bg-slate-800/80 border-slate-700' : 'bg-white border-slate-200'} space-y-3`}>
                <div className="flex justify-between items-center">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Inverted Index Metrics</h3>
                  <button onClick={handleTestConnection} className="text-[10px] text-indigo-400 hover:text-indigo-300">
                    Refresh
                  </button>
                </div>
                <div className="space-y-2 text-xs">
                  {[
                    ['Document Count', (statsData?.num_docs ?? statsData?.doc_count ?? 270509).toLocaleString() + ' articles'],
                    ['Index Build Time', `${statsData?.build_time_secs ?? statsData?.build_time_s ?? 207.04} s (3.45 min)`],
                    ['Inverted Index Size', statsData?.index_size_human ?? `${statsData?.index_size_mb ?? 830.11} MB`],
                    ['Raw Corpus Plaintext', `${statsData?.corpus_size_mb ?? 523.67} MB`],
                    ['Total Vocabulary Terms', (statsData?.num_unique_terms ?? 1160978).toLocaleString() + ' terms'],
                    ['Postings Compression', statsData?.postings_compressed ? 'Yes (Delta + VByte)' : 'Raw Little-Endian (Tier D Ready)']
                  ].map(([label, val]) => (
                    <div key={label} className="flex justify-between py-1 border-b border-slate-800/40 last:border-0">
                      <span className="text-slate-400">{label}</span>
                      <span className="font-bold text-slate-200">{val}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Tab 3: Settings */}
          {activeTab === 'settings' && (
            <div className="space-y-4">
              <h2 className="text-lg font-extrabold tracking-tight">Settings</h2>

              {/* Server Connection Card */}
              <div className={`p-4 rounded-2xl border ${isDark ? 'bg-slate-800/80 border-slate-700' : 'bg-white border-slate-200'} space-y-3`}>
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Server Connection</h3>
                <p className="text-xs text-slate-400">
                  Specify laptop LAN IP (e.g. http://192.168.1.50:8000/) or Android emulator default (http://10.0.2.2:8000/)
                </p>
                <input
                  type="text"
                  value={serverUrl}
                  onChange={(e) => setServerUrl(e.target.value)}
                  className={`w-full px-3 py-2 text-xs rounded-xl border outline-none ${isDark ? 'bg-slate-900 border-slate-700 text-white' : 'bg-slate-100 border-slate-200 text-slate-900'}`}
                />
                <button
                  onClick={handleTestConnection}
                  disabled={testingConn}
                  className="w-full py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition disabled:opacity-50"
                >
                  {testingConn ? 'Testing /stats...' : 'Test Connection (/stats)'}
                </button>

                {testResult && (
                  <div className="p-2.5 rounded-xl bg-emerald-950/80 border border-emerald-700/60 text-emerald-200 text-xs flex items-start space-x-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-semibold">{testResult.message}</p>
                      <p className="text-[10px] text-emerald-300/80">Round-trip ping: {testResult.latency} ms</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Results Per Page */}
              <div className={`p-4 rounded-2xl border ${isDark ? 'bg-slate-800/80 border-slate-700' : 'bg-white border-slate-200'} space-y-2`}>
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Results Per Page (k)</h3>
                <div className="flex gap-2">
                  {[10, 20, 50].map((k) => (
                    <button
                      key={k}
                      onClick={() => setResultsK(k)}
                      className={`flex-1 py-1.5 rounded-xl text-xs font-semibold transition ${resultsK === k ? 'bg-indigo-600 text-white' : isDark ? 'bg-slate-900 text-slate-400' : 'bg-slate-100 text-slate-700'}`}
                    >
                      {k}
                    </button>
                  ))}
                </div>
              </div>

              {/* Clear History */}
              <div className={`p-4 rounded-2xl border ${isDark ? 'bg-slate-800/80 border-slate-700' : 'bg-white border-slate-200'} space-y-2`}>
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">Search History</h3>
                <button
                  onClick={() => setSearchHistory([])}
                  className="w-full py-2 rounded-xl border border-red-500/40 text-red-400 hover:bg-red-500/10 font-semibold text-xs transition flex items-center justify-center space-x-1.5"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Clear Search History</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Bottom Navigation Bar */}
        <div className={`px-6 py-2.5 border-t ${isDark ? 'bg-slate-900 border-slate-800' : 'bg-white border-slate-200'} flex justify-around items-center`}>
          <button
            onClick={() => setActiveTab('search')}
            className={`flex flex-col items-center space-y-1 transition ${activeTab === 'search' ? 'text-indigo-400' : 'text-slate-500 hover:text-slate-300'}`}
          >
            <Search className="w-5 h-5" />
            <span className="text-[10px] font-semibold">Search</span>
          </button>
          <button
            onClick={() => setActiveTab('stats')}
            className={`flex flex-col items-center space-y-1 transition ${activeTab === 'stats' ? 'text-indigo-400' : 'text-slate-500 hover:text-slate-300'}`}
          >
            <BarChart3 className="w-5 h-5" />
            <span className="text-[10px] font-semibold">Stats</span>
          </button>
          <button
            onClick={() => setActiveTab('settings')}
            className={`flex flex-col items-center space-y-1 transition ${activeTab === 'settings' ? 'text-indigo-400' : 'text-slate-500 hover:text-slate-300'}`}
          >
            <SettingsIcon className="w-5 h-5" />
            <span className="text-[10px] font-semibold">Settings</span>
          </button>
        </div>
      </div>
    </div>
  );
}
