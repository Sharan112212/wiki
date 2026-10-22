# WikiSearch - Android Client for Local Wikipedia Inverted Index

**WikiSearch** is a native Android client built with Kotlin, Jetpack Compose, and Material 3 for searching a custom inverted index over Simple English Wikipedia with BM25 keyword ranking and exact phrase matching.

---

## Architecture & Tech Stack
- **Architecture**: MVVM with Repository Pattern & Coroutines Flow
- **UI**: 100% Jetpack Compose, Material 3, Material You Dynamic Themes (Light/Dark support)
- **Networking**: Retrofit 2 + OkHttp 4 + Gson with configurable timeouts (5s connect / 15s read)
- **Persistence**: Preferences DataStore for server configuration, theme preference, and search history
- **Navigation**: Jetpack Navigation Compose with edge-to-edge support
- **Package**: `com.team.wikisearch`

---

## Quick Start & Backend Configuration

### 1. Running the Mock Server
For local testing before connecting your laptop's C++/Python/Java search backend:
```bash
pip install fastapi uvicorn
python3 mock_server.py
```
This starts a mock server on `http://0.0.0.0:8000`.

### 2. Laptop LAN & Emulator Setup
- **Android Emulator**: Set the server URL in app Settings to:
  `http://10.0.2.2:8000/`
- **Physical Device (Wi-Fi)**:
  1. Ensure your laptop and phone are on the **same Wi-Fi network**.
  2. Find your laptop LAN IP address:
     - **Windows**: Run `ipconfig` (e.g. `192.168.1.50`)
     - **macOS / Linux**: Run `ifconfig` or `ip a` (e.g. `192.168.1.50`)
  3. Allow port `8000` through your laptop firewall.
  4. Open WikiSearch -> Settings tab -> Set base URL to `http://<YOUR-LAN-IP>:8000/` (e.g. `http://192.168.1.50:8000/`).
  5. Tap **Test connection (/stats)**.

---

## API Contract Specification

1. **`GET /search?q={query}&mode={keyword|phrase}&k=10`**
   - **Response**:
     ```json
     {
       "took_ms": 4.2,
       "total": 1873,
       "results": [
         {
           "id": 12,
           "title": "Solar eclipse",
           "score": 11.4,
           "snippet": "A solar <b>eclipse</b> occurs when..."
         }
       ]
     }
     ```
2. **`GET /article/{id}`**
   - **Response**:
     ```json
     {
       "id": 12,
       "title": "Solar eclipse",
       "text": "A solar eclipse occurs when the Moon passes between Earth and the Sun..."
     }
     ```
3. **`GET /stats`**
   - **Response**:
     ```json
     {
       "doc_count": 200000,
       "build_time_s": 412.5,
       "index_size_mb": 310.2,
       "corpus_size_mb": 650.0,
       "ratio": 0.48,
       "compressed": true
     }
     ```

---

## Building the Debug APK

To rebuild the debug APK locally:
```bash
./gradlew assembleDebug
```
The compiled APK will be output at:
`app/build/outputs/apk/debug/app-debug.apk`

Copy to output directory:
```bash
mkdir -p /output
cp app/build/outputs/apk/debug/app-debug.apk /output/WikiSearch-debug.apk
```

---

## Testing Checklist

- [x] **Keyword Search**: Ranked BM25 results with title, rank badge (#1), score chip, and bold snippet matches.
- [x] **Phrase Search & Quote Auto-Switch**: Wrapping query in double quotes (e.g. `"albert einstein"`) auto-switches mode to `Phrase`, strips quotes, and shows notice banner.
- [x] **UI States**: Idle with sample chips, Loading shimmer cards, Empty state with retry hint, and Error state with readable server exception.
- [x] **Article Reader**: Full scrollable text, query term highlighting, share action, font-size adjustment buttons (A-/A+), and CC BY-SA 4.0 footer link.
- [x] **Settings**: Editable base URL with live `/stats` test connection, k selector (10/20/50), system/light/dark theme toggle, and search history clearing.
- [x] **Stats Tab**: Complete index metrics display and comparison between server BM25 latency vs end-to-end app round-trip latency.

---

## License & Wikipedia Attribution
Articles and text snippets provided by this application are sourced from Simple English Wikipedia and licensed under **Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)**.
Full license text: https://creativecommons.org/licenses/by-sa/4.0/
