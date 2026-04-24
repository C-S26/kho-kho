"""
Kho Kho Live Scoreboard — Production Backend
Real-time state via polling. Control panel at /control (hidden from display).
"""

from flask import Flask, render_template, jsonify, request, Response
import time, os, json
from werkzeug.utils import secure_filename

app = Flask(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────
UPLOAD_FOLDER   = "static/logos"
TEAMS_FILE      = "teams.json"
HISTORY_FILE    = "match_history.json"
ALLOWED_EXT     = {"png","jpg","jpeg","gif","webp"}
MAX_LOGO_BYTES  = 5 * 1024 * 1024   # 5 MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ── Durations ──────────────────────────────────────────────────────────────
TURN_DURATION  = 7 * 60        # 7 min
BREAK_DURATION = 2 * 60 + 59  # 2 min 59 s

# ── Persistence helpers ────────────────────────────────────────────────────
def _load(path, default):
    try:
        if os.path.isfile(path):
            with open(path) as f:
                return json.load(f)
    except Exception:
        pass
    return default

def _save(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

teams_list   = _load(TEAMS_FILE, [])
match_history = _load(HISTORY_FILE, [])

# ── Game state ─────────────────────────────────────────────────────────────
def _blank_team(name="", side="l"):
    return {"name": name, "side": side, "score": 0}

game_state = {
    "teams":        [_blank_team("", "l"), _blank_team("", "r")],
    "start_time":   None,
    "paused_time":  TURN_DURATION,
    "running":      False,
    "phase":        "turn",        # "turn" | "break"
    "turn_number":  1,
    "total_turns":  8,
    "active_team":  0,             # 0 or 1 (chasing team index)
    "match_started": False,
    "match_over":   False,
    "winner":       None,
    "sound_enabled": True,
    "event_name":   "KHO KHO CHAMPIONSHIP",
    "venue":        "",
    "match_number": 1,
}

# ── Timer helpers ──────────────────────────────────────────────────────────
def _phase_duration():
    return TURN_DURATION if game_state["phase"] == "turn" else BREAK_DURATION

def _get_time():
    if not game_state["running"]:
        return game_state["paused_time"]
    elapsed   = time.monotonic() - game_state["start_time"]
    remaining = _phase_duration() - elapsed
    if remaining <= 0:
        _switch_phase()
        game_state["running"] = not game_state["match_over"]
        return game_state["paused_time"]
    return int(remaining)

def _switch_phase():
    if game_state["phase"] == "turn":
        game_state["phase"]       = "break"
        game_state["paused_time"] = BREAK_DURATION
    else:
        game_state["phase"]       = "turn"
        game_state["paused_time"] = TURN_DURATION
        game_state["turn_number"] += 1
        game_state["active_team"] = 1 - game_state["active_team"]
        if game_state["turn_number"] > game_state["total_turns"]:
            _end_match()
            return
    game_state["start_time"] = time.monotonic()

def _end_match():
    game_state["running"]    = False
    game_state["match_over"] = True
    s0 = game_state["teams"][0]["score"]
    s1 = game_state["teams"][1]["score"]
    if s0 > s1:
        game_state["winner"] = game_state["teams"][0]["name"]
    elif s1 > s0:
        game_state["winner"] = game_state["teams"][1]["name"]
    else:
        game_state["winner"] = "DRAW"
    record = {
        "team1":    game_state["teams"][0]["name"],
        "team2":    game_state["teams"][1]["name"],
        "score1":   s0,
        "score2":   s1,
        "winner":   game_state["winner"],
        "event":    game_state["event_name"],
        "match_no": game_state["match_number"],
        "timestamp": time.strftime("%Y-%m-%d %H:%M"),
    }
    match_history.insert(0, record)
    if len(match_history) > 50:
        match_history.pop()
    _save(HISTORY_FILE, match_history)

# ── Logo helper ────────────────────────────────────────────────────────────
def _logo_url(name):
    if not name:
        return "/static/default_logo.png"
    fn = name.strip().lower().replace(" ", "_") + ".png"
    fp = os.path.join(UPLOAD_FOLDER, fn)
    if os.path.isfile(fp):
        return f"/static/logos/{fn}"
    return "/static/default_logo.png"

def _allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

# ══════════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════════

@app.route("/")
def display():
    """TV / audience display — no control UI."""
    return render_template("display.html")

@app.route("/control")
def control():
    """Operator control panel — separate URL, not linked from display."""
    return render_template("control.html")

# ── State ──────────────────────────────────────────────────────────────────
@app.route("/state")
def state():
    t = _get_time()
    return jsonify({
        "teams": [
            {"name": g["name"], "score": g["score"], "logo": _logo_url(g["name"])}
            for g in game_state["teams"]
        ],
        "timer":         t,
        "running":       game_state["running"],
        "phase":         game_state["phase"],
        "turn_number":   game_state["turn_number"],
        "total_turns":   game_state["total_turns"],
        "active_team":   game_state["active_team"],
        "match_started": game_state["match_started"],
        "match_over":    game_state["match_over"],
        "winner":        game_state["winner"],
        "sound_enabled": game_state["sound_enabled"],
        "event_name":    game_state["event_name"],
        "venue":         game_state["venue"],
        "match_number":  game_state["match_number"],
        "server_time":   int(time.time() * 1000),
    })

# ── Timer control ──────────────────────────────────────────────────────────
@app.route("/start", methods=["POST"])
def start():
    if not game_state["running"] and not game_state["match_over"]:
        dur = _phase_duration()
        game_state["start_time"]   = time.monotonic() - (dur - game_state["paused_time"])
        game_state["running"]      = True
        game_state["match_started"] = True
    return jsonify({"ok": True})

@app.route("/pause", methods=["POST"])
def pause():
    if game_state["running"]:
        game_state["paused_time"] = _get_time()
        game_state["running"]     = False
    return jsonify({"ok": True})

@app.route("/reset", methods=["POST"])
def reset():
    names = [t["name"] for t in game_state["teams"]]
    game_state["teams"]        = [_blank_team(names[0], "l"), _blank_team(names[1], "r")]
    game_state["paused_time"]  = TURN_DURATION
    game_state["running"]      = False
    game_state["start_time"]   = None
    game_state["phase"]        = "turn"
    game_state["turn_number"]  = 1
    game_state["active_team"]  = 0
    game_state["match_started"] = False
    game_state["match_over"]   = False
    game_state["winner"]       = None
    return jsonify({"ok": True})

@app.route("/end_turn", methods=["POST"])
def end_turn():
    _switch_phase()
    if not game_state["match_over"]:
        game_state["running"] = True
    return jsonify({"ok": True})

# ── Score ──────────────────────────────────────────────────────────────────
@app.route("/score", methods=["POST"])
def score():
    d = request.get_json(silent=True) or {}
    t = d.get("team")
    if t not in (0, 1):
        return jsonify({"error": "invalid team"}), 400
    game_state["teams"][t]["score"] += 1
    return jsonify({"ok": True, "score": game_state["teams"][t]["score"]})

@app.route("/score/decrement", methods=["POST"])
def score_dec():
    d = request.get_json(silent=True) or {}
    t = d.get("team")
    if t not in (0, 1):
        return jsonify({"error": "invalid team"}), 400
    if game_state["teams"][t]["score"] > 0:
        game_state["teams"][t]["score"] -= 1
    return jsonify({"ok": True, "score": game_state["teams"][t]["score"]})

@app.route("/score/set", methods=["POST"])
def score_set():
    d = request.get_json(silent=True) or {}
    t   = d.get("team")
    val = d.get("value")
    if t not in (0, 1) or not isinstance(val, int) or val < 0:
        return jsonify({"error": "invalid"}), 400
    game_state["teams"][t]["score"] = val
    return jsonify({"ok": True})

# ── Teams ──────────────────────────────────────────────────────────────────
@app.route("/teams")
def get_teams():
    return jsonify({"teams": teams_list})

@app.route("/add_team", methods=["POST"])
def add_team():
    d    = request.get_json(silent=True) or {}
    name = (d.get("name") or "").strip()
    if not name:
        return jsonify({"error": "empty name"}), 400
    if len(name) > 60:
        return jsonify({"error": "name too long"}), 400
    if name not in teams_list:
        teams_list.append(name)
        _save(TEAMS_FILE, teams_list)
    return jsonify({"teams": teams_list})

@app.route("/delete_team", methods=["POST"])
def delete_team():
    d    = request.get_json(silent=True) or {}
    name = (d.get("name") or "").strip()
    if name in teams_list:
        teams_list.remove(name)
        _save(TEAMS_FILE, teams_list)
    for i, t in enumerate(game_state["teams"]):
        if t["name"] == name and t["score"] == 0 and not game_state["running"]:
            game_state["teams"][i] = _blank_team("", t["side"])
    return jsonify({"ok": True, "teams": teams_list})

@app.route("/set_match", methods=["POST"])
def set_match():
    d     = request.get_json(silent=True) or {}
    t1    = (d.get("team1") or "").strip()
    t2    = (d.get("team2") or "").strip()
    turns = d.get("total_turns", 8)
    event = (d.get("event_name") or "KHO KHO CHAMPIONSHIP").strip()
    venue = (d.get("venue") or "").strip()
    match_no = d.get("match_number", 1)

    if not t1 or not t2:
        return jsonify({"error": "missing team name"}), 400
    if t1 == t2:
        return jsonify({"error": "teams must differ"}), 400
    if not isinstance(turns, int) or not (2 <= turns <= 16):
        turns = 8

    changed = False
    for n in (t1, t2):
        if n not in teams_list:
            teams_list.append(n); changed = True
    if changed:
        _save(TEAMS_FILE, teams_list)

    game_state.update({
        "teams":        [_blank_team(t1, "l"), _blank_team(t2, "r")],
        "phase":        "turn",
        "paused_time":  TURN_DURATION,
        "start_time":   None,
        "running":      False,
        "turn_number":  1,
        "total_turns":  turns,
        "active_team":  0,
        "match_started": False,
        "match_over":   False,
        "winner":       None,
        "event_name":   event,
        "venue":        venue,
        "match_number": match_no,
    })
    return jsonify({"ok": True})

# ── Event settings ─────────────────────────────────────────────────────────
@app.route("/set_event", methods=["POST"])
def set_event():
    d = request.get_json(silent=True) or {}
    if "event_name"   in d: game_state["event_name"]   = str(d["event_name"]).strip()
    if "venue"        in d: game_state["venue"]        = str(d["venue"]).strip()
    if "match_number" in d: game_state["match_number"] = int(d["match_number"])
    return jsonify({"ok": True})

# ── Sound ──────────────────────────────────────────────────────────────────
@app.route("/toggle_sound", methods=["POST"])
def toggle_sound():
    game_state["sound_enabled"] = not game_state["sound_enabled"]
    return jsonify({"ok": True, "sound_enabled": game_state["sound_enabled"]})

# ── Declare winner ─────────────────────────────────────────────────────────
@app.route("/declare_winner", methods=["POST"])
def declare_winner():
    d = request.get_json(silent=True) or {}
    t = d.get("team")
    if t not in (0, 1):
        return jsonify({"error": "invalid"}), 400
    game_state["running"]    = False
    game_state["match_over"] = True
    game_state["winner"]     = game_state["teams"][t]["name"]
    # Save to history
    s0, s1 = game_state["teams"][0]["score"], game_state["teams"][1]["score"]
    record = {
        "team1": game_state["teams"][0]["name"], "team2": game_state["teams"][1]["name"],
        "score1": s0, "score2": s1, "winner": game_state["winner"],
        "event": game_state["event_name"], "match_no": game_state["match_number"],
        "timestamp": time.strftime("%Y-%m-%d %H:%M"),
    }
    match_history.insert(0, record)
    if len(match_history) > 50: match_history.pop()
    _save(HISTORY_FILE, match_history)
    return jsonify({"ok": True})

# ── History ────────────────────────────────────────────────────────────────
@app.route("/history")
def history():
    return jsonify({"history": match_history})

@app.route("/history/clear", methods=["POST"])
def clear_history():
    match_history.clear()
    _save(HISTORY_FILE, match_history)
    return jsonify({"ok": True})

# ── Logo upload ────────────────────────────────────────────────────────────
@app.route("/upload_logo", methods=["POST"])
def upload_logo():
    team = (request.form.get("team") or "").strip()
    file = request.files.get("logo")
    if not team or not file:
        return jsonify({"error": "missing team or file"}), 400
    if not _allowed(file.filename):
        return jsonify({"error": "use png/jpg/gif/webp"}), 400
    data = file.read()
    if len(data) > MAX_LOGO_BYTES:
        return jsonify({"error": "file too large (max 5 MB)"}), 400
    fn   = team.strip().lower().replace(" ", "_") + ".png"
    path = os.path.join(UPLOAD_FOLDER, fn)
    with open(path, "wb") as f:
        f.write(data)
    return jsonify({"ok": True, "path": f"/static/logos/{fn}"})

# ── Timer adjustment ───────────────────────────────────────────────────────
@app.route("/adjust_timer", methods=["POST"])
def adjust_timer():
    d      = request.get_json(silent=True) or {}
    delta  = int(d.get("delta", 0))   # seconds, positive = add, negative = subtract
    cur    = _get_time()
    newval = max(0, min(cur + delta, _phase_duration()))
    game_state["paused_time"] = newval
    if game_state["running"]:
        dur = _phase_duration()
        game_state["start_time"] = time.monotonic() - (dur - newval)
    return jsonify({"ok": True, "timer": newval})

#if __name__ == "__main__":
    #app.run(debug=False, host="0.0.0.0", port=5000, threaded=True)

if __name__ == "__main__":
    app.run(debug=False,host="0.0.0.0", port=int(os.environ.get("PORT", 5000)),threaded=True)