# start.gg Tournament Stats

A simple desktop app that pulls every tournament you've organized on [start.gg](https://start.gg) and totals the attendees — no more manually deleting rows from a spreadsheet.

Built with [PyWebView](https://pywebview.flowrl.com/) (Python backend, HTML/CSS/JS frontend in a native window).

![screenshot placeholder](docs/screenshot.png)

---

## Features

- 🔐 Credentials stay in memory — never written to disk
- ⚡ Filters server-side via the start.gg `ownerId` field, so you only get *your* tournaments
- 📊 Live progress while paginating
- 💾 One-click CSV export with native save dialog
- 🖥️ Real desktop window, no browser required

---

## Run from source

Requires **Python 3.10+**.

```bash
git clone https://github.com/YOUR-USERNAME/startgg-tournament-stats.git
cd startgg-tournament-stats
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

### Getting a start.gg API token

1. Log in to start.gg
2. Go to **Settings → Developer Settings**
3. Click **Create New Token**, give it a description, copy the value
4. Paste it into the app

### Finding your user slug

It's the string after `start.gg/user/` in your profile URL.
Example: `https://start.gg/user/abc1234d` → slug is `abc1234d`.

---

## Build a standalone app (PyInstaller)

To produce a double-clickable `.exe` (Windows) or `.app` (macOS):

```bash
pip install pyinstaller
pyinstaller --noconfirm --windowed --name "StartGG Stats" \
  --add-data "ui:ui" \
  app.py
```

The bundle lands in `dist/StartGG Stats/`.

> **Note:** unsigned binaries trigger a warning on first launch (Gatekeeper on macOS, SmartScreen on Windows). Users can right-click → Open (mac) or click "More info → Run anyway" (Windows). Code signing requires a paid developer certificate.

> macOS builds must be made on macOS; Windows builds on Windows.

---

## Project structure

```
.
├── app.py              # PyWebView entry point + JS↔Python bridge
├── api.py              # start.gg GraphQL client
├── ui/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── requirements.txt
└── README.md
```

---

## License

MIT
