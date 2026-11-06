import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
WRITE_SECRET = os.environ.get("SCOREBOARD_WRITE_SECRET")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/api/score", methods=["POST"])
def submit_score():
    data = request.get_json(force=True)

    if data.get("secret") != WRITE_SECRET:
        return jsonify({"status": "error", "detail": "unauthorized"}), 401

    required = ["nickname", "tier", "score", "minutesTaken", "hintUsed", "attemptCount"]
    if not all(field in data for field in required):
        return jsonify({"status": "error", "detail": "missing fields"}), 400

    payload = {
        "nickname": str(data["nickname"])[:24],
        "tier": data["tier"],
        "score": int(data["score"]),
        "minutes_taken": float(data["minutesTaken"]),
        "hint_used": bool(data["hintUsed"]),
        "attempt_count": int(data["attemptCount"])
    }

    res = requests.post(f"{SUPABASE_URL}/rest/v1/scores", headers=HEADERS, json=payload)

    if res.status_code not in (200, 201):
        return jsonify({"status": "error", "detail": res.text}), 500

    return jsonify({"status": "success"})

@app.route("/api/leaderboard", methods=["GET"])
def leaderboard():
    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/scores?select=*&order=created_at.desc",
        headers=HEADERS
    )
    if res.status_code != 200:
        return jsonify({"status": "error", "detail": res.text}), 500

    rows = res.json()

    # Keep only each player's best score per tier.
    best = {}
    for row in rows:
        key = (row["nickname"], row["tier"])
        if key not in best or row["score"] > best[key]["score"]:
            best[key] = row

    # Aggregate into per-player totals.
    players = {}
    for row in best.values():
        nickname = row["nickname"]
        if nickname not in players:
            players[nickname] = {"nickname": nickname, "total_score": 0, "tiers": {}}
        players[nickname]["total_score"] += row["score"]
        players[nickname]["tiers"][row["tier"]] = {
            "score": row["score"],
            "minutes_taken": row["minutes_taken"],
            "hint_used": row["hint_used"],
            "attempt_count": row["attempt_count"]
        }

    leaderboard_list = sorted(players.values(), key=lambda p: p["total_score"], reverse=True)
    return jsonify({"leaderboard": leaderboard_list})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5001)))