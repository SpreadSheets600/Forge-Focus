# ⚡ FocusForge

A beautiful, cross-platform desktop productivity app that helps you stay focused by tracking your time and blocking distractions.

## Features

- 📊 **Time Tracking**: Automatic tracking of desktop apps and websites
- 🎯 **Focus Sessions**: Create timed focus sessions with customizable blocklists
- 🚫 **Smart Blocking**: Block distracting apps and websites during focus time
- ⚠️ **Warning Dialogs**: Shows a warning when blocked apps are opened (instead of immediate termination)
- 📅 **Scheduling**: Set up automatic focus sessions at specific times
- 📈 **Analytics**: Beautiful graphs showing your productivity patterns
- 🔒 **Strict Mode**: Requires passphrase to exit focus sessions early
- 🌐 **Browser Extension**: Tracks website usage and enforces blocks
- Per-app and per-website daily time limits (auto block/close on exceed)
- 🎨 **Beautiful UI**: Modern, aesthetic interface built with Flet

## 🏗️ Architecture

```
         ┌────────────────────────┐
         │  BROWSER EXTENSION     │
         │  (Chrome/Firefox)      │
         └────────────┬───────────┘
                      ↓
             (Local REST API)

┌──────────────────────────────────────────┐
│         PYTHON MAIN APP (Flet UI)        │
└──────────────┬───────────────────────────┘
               │
      ┌────────┴─────────┐
      ↓                  ↓
Background Tracker   Background Blocker
  (psutil)            (process killer)
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- UV package manager (automatically installed)
- Chrome or Firefox browser

### Installation

1. **Clone or navigate to the project**:
```bash
cd focusforge
```

2. **Install dependencies with UV**:
```bash
uv sync
```

3. **Run FocusForge**:
```bash
uv run focusforge
```

Or use the Python module:
```bash
uv run python -m focusforge.main
```

### Browser Extension Setup

#### Chrome/Edge

1. Open Chrome and go to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `extension/chrome` folder
5. The FocusForge extension is now installed! 🎉

#### Firefox

1. Open Firefox and go to `about:debugging#/runtime/this-firefox`
2. Click "Load Temporary Add-on"
3. Navigate to `extension/chrome` and select `manifest.json`
4. The extension is now active!

## 📖 Usage

### Starting a Focus Session

1. Launch FocusForge
2. Navigate to **Focus Mode**
3. Set your session duration (15-180 minutes)
4. Enable **Strict Mode** if you want to require a passphrase to stop
5. Click **Start Focus Session**
6. Set an optional Daily Limit (minutes) for any app or website. When the daily time is reached:
  - The website is blocked in the browser extension.
  - The desktop application process is closed automatically and re-closed if restarted.

### Managing Blocklists

1. Go to **Blocklist** tab
2. Add apps by their process name (e.g., `chrome.exe`, `spotify.exe`)
3. Add websites by domain (e.g., `youtube.com`, `twitter.com`)
4. Blocked items will be enforced during focus sessions

### Scheduling Focus Times

1. Navigate to **Schedule** tab
2. Click **Add Schedule**
3. Set start/end times and days of week
4. Select which apps/websites to block
5. The schedule will automatically activate!

### Stopping a Focus Session

- **Normal mode**: Click "Stop Focus Session"
- **Strict mode**: Type the passphrase: `I choose discipline today and commit to my goals`

### Viewing Analytics

1. Go to **Dashboard**
2. View your daily app and website usage
3. See your productivity score
4. Track focus session completion rate

## 🎯 Key Features Explained

### App Tracking

FocusForge automatically tracks:
- Active application name
- Window title
- Time spent per app
- All data stored locally in SQLite

### Website Blocking

The browser extension:
- Tracks visited websites
- Sends data to local API
- Redirects blocked sites to a motivational "Focus Time" page
- Shows session progress and quotes

### Strict Mode

When enabled:
- Cannot stop focus session for 15 minutes minimum
- Requires typing full passphrase to exit
- Helps maintain discipline during difficult moments

### Process Blocking

The blocker service:
- Monitors running processes every second
- Terminates blocked apps automatically
- Prevents launching blocked applications

## 🛠️ Development

### Project Structure

```
focusforge/
├── src/focusforge/
│   ├── main.py              # Application entry point
│   ├── database/            # SQLAlchemy models
│   ├── services/            # Background services
│   │   ├── app_tracker.py   # Desktop app tracking
│   │   ├── blocker.py       # App/website blocking
│   │   └── scheduler.py     # Scheduled sessions
│   ├── api/                 # FastAPI backend
│   │   └── server.py        # REST API endpoints
│   ├── ui/                  # Flet UI
│   │   └── main_window.py   # Main interface
│   └── utils/               # Utilities
│       ├── analytics.py     # Plotly graphs
│       └── helpers.py       # Helper functions
├── extension/               # Browser extension
│   └── chrome/
│       ├── manifest.json    # Extension config
│       ├── background.js    # Service worker
│       ├── content.js       # Content script
│       ├── popup.html       # Extension popup
│       └── blocked.html     # Blocked page
├── data/                    # SQLite database
└── pyproject.toml          # UV dependencies
```

### API Endpoints

The local API runs on `http://localhost:8765`:

- `POST /website-activity` - Log website activity
- `GET /website-activity/check-blocked/{domain}` - Check if site is blocked
- `POST /focus/start` - Start focus session
- `POST /focus/stop` - Stop focus session
- `GET /focus/status` - Get current focus status
- `GET /stats/daily` - Get daily statistics
- `GET /stats/weekly` - Get weekly statistics
- `GET /blocklist` - Get blocked items
- `POST /blocklist` - Add to blocklist
- `GET /schedules` - Get all schedules
- `POST /schedules` - Create schedule

### Running API Server Separately

```bash
uv run focusforge-api
```

## 🎨 Customization

### Color Scheme

Edit the theme in `src/focusforge/ui/main_window.py`:

```python
page.theme = ft.Theme(
    color_scheme=ft.ColorScheme(
        primary="#667eea",      # Primary color
        secondary="#764ba2",    # Secondary color
        background="#0a0a0a",   # Dark background
        surface="#1a1a1a",      # Card background
    ),
)
```

### Default Blocklists

Add default blocked items in the database initialization.

## 🐛 Troubleshooting

### Extension Can't Connect

- Ensure FocusForge app is running
- Check that API server started on port 8765
- Look for "API server started" message in console

### App Tracking Not Working

**Windows**: Install pywin32
```bash
uv add pywin32
```

**Linux**: Install python-xlib
```bash
uv add python-xlib
```

**macOS**: Install pyobjc
```bash
uv add pyobjc-framework-Cocoa
```

### Apps Not Being Blocked

- Check process name matches exactly (case-sensitive on some platforms)
- Ensure blocker service started successfully
- Some system apps cannot be terminated

## 📝 License

MIT License - Feel free to use and modify!

## 🙏 Credits

Built with:
- [Flet](https://flet.dev) - Beautiful UI framework
- [FastAPI](https://fastapi.tiangolo.com) - Modern API framework
- [SQLAlchemy](https://www.sqlalchemy.org) - Database ORM
- [Plotly](https://plotly.com) - Interactive graphs
- [psutil](https://github.com/giampaolo/psutil) - Process utilities
- [APScheduler](https://apscheduler.readthedocs.io) - Task scheduling

## 🚀 Future Enhancements

- [ ] Pomodoro timer integration
- [ ] Team/family sharing features
- [ ] Mobile companion app
- [ ] Cloud sync (optional)
- [ ] AI-powered productivity insights
- [ ] Gamification (achievements, streaks)
- [ ] Export reports (PDF/CSV)

---

**Stay focused. Stay productive. Build great things.** ⚡
