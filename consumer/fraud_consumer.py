"""
fraud_consumer.py
Consumes simulated transactions from Kafka, scores each one for fraud risk
using a multi-factor rule engine, and persists the result to PostgreSQL.

Run from the project root: python consumer/fraud_consumer.py
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg2
from confluent_kafka import Consumer

import config

# ---------------------------------------------------------------------------
# Fraud scoring config
# Each rule contributes points toward a 0-100 score. A transaction is
# flagged once the cumulative score crosses FLAG_THRESHOLD. Using several
# weighted signals (rather than one amount cutoff) means a single large-but-
# legitimate purchase doesn't get flagged on its own, while a combination of
# smaller red flags (e.g. odd hour + impossible travel) still gets caught.
# ---------------------------------------------------------------------------

FLAG_THRESHOLD = 50

CATEGORY_TYPICAL_MAX = {
    "Grocery": 2500, "Fuel": 1500, "Electronics": 25000, "Online Retail": 8000,
    "Restaurant": 900, "Airtime & Data": 500, "Clothing": 4000,
    "Bills & Insurance": 5000, "ATM Withdrawal": 5000,
}

VELOCITY_WINDOW_MINUTES = 10
VELOCITY_COUNT_THRESHOLD = 4
TRAVEL_WINDOW_MINUTES = 60


def get_connection():
    return psycopg2.connect(config.get_db_dsn())


def fetch_recent_account_history(cur, account_id: str, minutes: int):
    """Transactions for this account in the last `minutes`, most recent first."""
    cur.execute(
        """
        SELECT city, amount, timestamp
        FROM transactions
        WHERE account_id = %s
          AND timestamp >= %s
        ORDER BY timestamp DESC
        """,
        (account_id, datetime.now(timezone.utc) - timedelta(minutes=minutes)),
    )
    return cur.fetchall()


def score_transaction(txn: dict, history: list) -> tuple[int, list[str]]:
    """
    Returns (score 0-100, reasons[]). `history` is this account's recent
    transactions (already inserted ones - the current txn is not in it yet,
    since scoring happens before the insert).
    """
    score = 0
    reasons = []
    now = datetime.now(timezone.utc)

    # --- Rule 1: amount well above what's typical for the category ---
    typical_max = CATEGORY_TYPICAL_MAX.get(txn["merchant_category"], 5000)
    if txn["amount"] > typical_max * 5:
        score += 35
        reasons.append(f"Amount R{txn['amount']:.2f} is over 5x typical for {txn['merchant_category']}")
    elif txn["amount"] > typical_max * 2:
        score += 15
        reasons.append(f"Amount R{txn['amount']:.2f} is over 2x typical for {txn['merchant_category']}")

    # --- Rule 2: odd-hour transaction (01:00-04:59) ---
    txn_time = datetime.fromisoformat(txn["timestamp"])
    if 1 <= txn_time.hour <= 4:
        score += 15
        reasons.append(f"Transaction occurred at {txn_time.strftime('%H:%M')} (unusual hour)")

    # --- Rule 3: velocity - too many transactions in a short window ---
    velocity_cutoff = now - timedelta(minutes=VELOCITY_WINDOW_MINUTES)
    recent_velocity = [row for row in history if row[2] >= velocity_cutoff]
    if len(recent_velocity) >= VELOCITY_COUNT_THRESHOLD:
        score += 25
        reasons.append(
            f"{len(recent_velocity)} transactions on this account in the last {VELOCITY_WINDOW_MINUTES} min"
        )

    # --- Rule 4: impossible travel - a different city within the travel window ---
    recent_cities = {row[0] for row in history if row[0] != txn["city"]}
    if recent_cities:
        score += 30
        reasons.append(
            f"Account active in {', '.join(sorted(recent_cities))} within "
            f"{TRAVEL_WINDOW_MINUTES} min of this transaction in {txn['city']}"
        )

    # --- Rule 5: card testing - repeated very small charges ---
    small_recent = [row for row in recent_velocity if float(row[1]) < 100]
    if txn["amount"] < 100 and len(small_recent) >= 2:
        score += 20
        reasons.append("Pattern of repeated small charges (possible card testing)")

    return min(score, 100), reasons


def persist_transaction(cur, txn: dict, fraud_score: int, reasons: list[str]):
    is_flagged = fraud_score >= FLAG_THRESHOLD
    cur.execute(
        """
        INSERT INTO transactions (
            transaction_id, account_id, account_holder, amount, currency,
            merchant_name, merchant_category, city, province,
            transaction_type, channel, timestamp,
            is_fraud_simulated, fraud_score, is_flagged, flag_reasons
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (transaction_id) DO NOTHING
        """,
        (
            txn["transaction_id"], txn["account_id"], txn["account_holder"],
            txn["amount"], txn["currency"], txn["merchant_name"], txn["merchant_category"],
            txn["city"], txn["province"], txn["transaction_type"], txn["channel"],
            txn["timestamp"], txn.get("is_fraud_simulated", False),
            fraud_score, is_flagged, " | ".join(reasons) if reasons else None,
        ),
    )

    if is_flagged:
        severity = "high" if fraud_score >= 75 else "medium"
        cur.execute(
            """
            INSERT INTO fraud_alerts (transaction_id, fraud_score, reasons, severity)
            VALUES (%s, %s, %s, %s)
            """,
            (txn["transaction_id"], fraud_score, " | ".join(reasons), severity),
        )


def run():
    consumer = Consumer({
        "bootstrap.servers": config.KAFKA_BOOTSTRAP_SERVERS,
        "group.id": "fraud-detection-group",
        "auto.offset.reset": "latest",
    })
    consumer.subscribe([config.KAFKA_TOPIC])

    conn = get_connection()
    conn.autocommit = True
    cur = conn.cursor()

    print(f"[consumer] Listening on topic '{config.KAFKA_TOPIC}'... (Ctrl+C to stop)")

    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print(f"[consumer] Error: {msg.error()}")
                continue

            txn = json.loads(msg.value().decode("utf-8"))
            history = fetch_recent_account_history(cur, txn["account_id"], TRAVEL_WINDOW_MINUTES)
            fraud_score, reasons = score_transaction(txn, history)
            persist_transaction(cur, txn, fraud_score, reasons)

            tag = "FLAGGED" if fraud_score >= FLAG_THRESHOLD else "ok"
            print(
                f"[consumer] {txn['account_holder']:<25} R{txn['amount']:>10,.2f}  "
                f"{txn['city']:<17} score={fraud_score:>3} [{tag}]"
            )

    except KeyboardInterrupt:
        print("\n[consumer] Stopped by user.")
    finally:
        cur.close()
        conn.close()
        consumer.close()


if __name__ == "__main__":
    run()
