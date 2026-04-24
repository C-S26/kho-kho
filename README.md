# Kho Kho Live Scoreboard — Fresh Build

## Quick Start

```bash
pip install flask
python app.py
```

Then open:
- **TV/Display** → `http://localhost:5000/`
- **Control Panel** → `http://localhost:5000/control`  ← operator only, never shown on TV

---

## Architecture

```
app.py                  ← Flask backend (all game state & APIs)
templates/
  display.html          ← TV scoreboard (full-screen, no control link)
  control.html          ← Operator panel (3-column layout)
static/
  logos/                ← Team logo uploads stored here
teams.json              ← Persisted team list (auto-created)
match_history.json      ← Persisted match history (auto-created)
```

---

## Features

### Display (TV)
- Full-screen dark scoreboard — no clutter, no control UI
- Smooth client-side timer (syncs every 500 ms, ticks locally between syncs)
- Animated spinning logo rings (stops when not chasing)
- Active chasing team highlighted with glow + spinning ring
- Live score pop animation on each point
- "LEADING" badge for the team ahead
- Turn progress dots (shows each turn done/current/pending)
- Break time banner overlay
- Confetti + winner overlay on match end
- Clock display in top-right

### Control Panel (Operator)
- **3-column layout**: Setup | Timer+Scores | Status+History
- Match setup: team selection, turns (4/8/12/16), event name, venue, match number
- Real-time timer with ring progress + local tick between syncs
- Timer adjust: ±30s and ±1m buttons
- Score +/− with keyboard shortcuts (Q/A Team A, P/L Team B)
- Manual score set (for corrections)
- End Turn / Break button
- Declare Winner manually (bypasses auto)
- Team management: add / delete teams (with chips display)
- Logo upload per team (any image format)
- Match history with event + timestamp (persistent across restarts)
- History clear button
- Sound toggle
- Open Display button

### Backend
- Persistent teams + history (JSON files survive restarts)
- Accurate server-side timer (monotonic clock)
- Auto phase switching (turn → break → turn → …)
- Auto match end after all turns
- Timer adjustment API
- Event name / venue stored in state

---

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/` | TV display |
| GET | `/control` | Operator control panel |
| GET | `/state` | Full game state JSON |
| POST | `/start` | Start/resume timer |
| POST | `/pause` | Pause timer |
| POST | `/reset` | Reset match (keeps teams) |
| POST | `/end_turn` | Force end current turn/break |
| POST | `/score` | `{"team":0}` — add point |
| POST | `/score/decrement` | Remove point |
| POST | `/score/set` | `{"team":0,"value":5}` — set score |
| POST | `/adjust_timer` | `{"delta":30}` — add/sub seconds |
| GET | `/teams` | Team list |
| POST | `/add_team` | `{"name":"..."}` |
| POST | `/delete_team` | `{"name":"..."}` |
| POST | `/set_match` | Configure match |
| POST | `/set_event` | Update event name/venue |
| POST | `/declare_winner` | `{"team":0}` |
| POST | `/toggle_sound` | Toggle sound flag |
| GET | `/history` | Match history |
| POST | `/history/clear` | Clear history |
| POST | `/upload_logo` | Multipart logo upload |

---

## TV / HDMI Setup

1. Open `http://<your-ip>:5000/` on the TV browser (full-screen / kiosk mode)
2. Open `http://<your-ip>:5000/control` on the operator laptop
3. Control panel URL is never shown or linked from the display

---

## Keyboard Shortcuts (Control Panel)

| Key | Action |
|-----|--------|
| Space | Play / Pause |
| Q | +1 point Team A |
| A | −1 point Team A |
| P | +1 point Team B |
| L | −1 point Team B |
| E | End current turn |
