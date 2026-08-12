"""
app.py
Flask dashboard for the real-time fraud detection ETL pipeline. Polls
PostgreSQL for live stats and serves an auto-refreshing dashboard UI.

Run from the project root: python dashboard/app.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2
import psycopg2.extras
from flask import Flask, jsonify, render_template

import config

app = Flask(__name__)
app.secret_key = config.FLASK_SECRET_KEY


def get_connection():
    return psycopg2.connect(config.get_db_dsn())


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/summary")
def api_summary():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM transactions")
    total_count, total_amount = cur.fetchone()

    cur.execute("SELECT COUNT(*) FROM transactions WHERE is_flagged = TRUE")
    flagged_count = cur.fetchone()[0]

    cur.execute("SELECT COALESCE(AVG(fraud_score), 0) FROM transactions")
    avg_score = cur.fetchone()[0]

    cur.execute(
        "SELECT COUNT(*) FROM transactions WHERE is_flagged = TRUE AND is_fraud_simulated = TRUE"
    )
    true_positives = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM transactions WHERE is_fraud_simulated = TRUE")
    total_simulated_fraud = cur.fetchone()[0]

    cur.close()
    conn.close()

    fraud_rate = (flagged_count / total_count * 100) if total_count else 0
    detection_rate = (true_positives / total_simulated_fraud * 100) if total_simulated_fraud else 0

    return jsonify({
        "total_transactions": total_count,
        "total_amount": float(total_amount),
        "flagged_count": flagged_count,
        "fraud_rate": round(fraud_rate, 2),
        "avg_fraud_score": round(float(avg_score), 1),
        "detection_rate": round(detection_rate, 1),
    })


@app.route("/api/recent")
def api_recent():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT transaction_id, account_holder, amount, merchant_name,
               merchant_category, city, province, channel, timestamp,
               fraud_score, is_flagged, flag_reasons
        FROM transactions
        ORDER BY timestamp DESC
        LIMIT 25
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    for row in rows:
        row["timestamp"] = row["timestamp"].isoformat()
        row["amount"] = float(row["amount"])
    return jsonify(rows)


@app.route("/api/alerts")
def api_alerts():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT a.alert_id, a.fraud_score, a.reasons, a.severity, a.created_at,
               t.account_holder, t.amount, t.city, t.merchant_name
        FROM fraud_alerts a
        JOIN transactions t ON a.transaction_id = t.transaction_id
        ORDER BY a.created_at DESC
        LIMIT 15
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    for row in rows:
        row["created_at"] = row["created_at"].isoformat()
        row["amount"] = float(row["amount"])
    return jsonify(rows)


@app.route("/api/by_city")
def api_by_city():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT city, COUNT(*) AS total, COUNT(*) FILTER (WHERE is_flagged) AS flagged
        FROM transactions
        GROUP BY city
        ORDER BY total DESC
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{"city": r[0], "total": r[1], "flagged": r[2]} for r in rows])


@app.route("/api/by_category")
def api_by_category():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT merchant_category, COUNT(*) AS total, COUNT(*) FILTER (WHERE is_flagged) AS flagged
        FROM transactions
        GROUP BY merchant_category
        ORDER BY total DESC
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{"category": r[0], "total": r[1], "flagged": r[2]} for r in rows])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=config.DASHBOARD_PORT, debug=True)
