"""
config.py
Shared configuration for the producer, consumer, and dashboard. Reads from
.env (see .env.example) with sensible local defaults.
"""

import os

from dotenv import load_dotenv

load_dotenv()

# --- PostgreSQL ---
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "fraud_etl")
POSTGRES_USER = os.getenv("POSTGRES_USER", "etl_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "etl_password")


def get_db_dsn() -> str:
    return (
        f"host={POSTGRES_HOST} port={POSTGRES_PORT} "
        f"dbname={POSTGRES_DB} user={POSTGRES_USER} password={POSTGRES_PASSWORD}"
    )


# --- Kafka ---
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "transactions")

# --- Simulation ---
TRANSACTIONS_PER_SECOND = float(os.getenv("TRANSACTIONS_PER_SECOND", "2"))
FRAUD_INJECTION_RATE = float(os.getenv("FRAUD_INJECTION_RATE", "0.05"))

# --- Dashboard ---
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "5000"))
