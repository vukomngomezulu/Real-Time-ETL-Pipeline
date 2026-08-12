"""
transaction_generator.py
Simulates real-time South African financial transactions and streams them
to a Kafka topic for downstream fraud detection.

Run from the project root: python producer/transaction_generator.py
"""

import json
import random
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from confluent_kafka import Producer

import config

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

CITIES = [
    {"city": "Richards Bay", "province": "KwaZulu-Natal"},
    {"city": "Durban", "province": "KwaZulu-Natal"},
    {"city": "Pietermaritzburg", "province": "KwaZulu-Natal"},
    {"city": "Empangeni", "province": "KwaZulu-Natal"},
    {"city": "Johannesburg", "province": "Gauteng"},
    {"city": "Pretoria", "province": "Gauteng"},
    {"city": "Cape Town", "province": "Western Cape"},
    {"city": "Stellenbosch", "province": "Western Cape"},
    {"city": "Gqeberha", "province": "Eastern Cape"},
    {"city": "East London", "province": "Eastern Cape"},
    {"city": "Bloemfontein", "province": "Free State"},
    {"city": "Polokwane", "province": "Limpopo"},
    {"city": "Nelspruit", "province": "Mpumalanga"},
    {"city": "Kimberley", "province": "Northern Cape"},
    {"city": "Esikawini", "province": "KwaZulu-Natal"},
]

FIRST_NAMES = [
    "Thabo", "Lindiwe", "Sipho", "Nomvula", "Ayanda", "Bongani", "Zanele",
    "Karabo", "Tshepo", "Naledi", "Mpho", "Refilwe", "Jacques", "Anika",
    "Pieter", "Carla", "Vuko", "Nokuthula", "Lwazi", "Palesa", "Kagiso",
    "Dineo", "Sibusiso", "Thandeka", "Johan", "Sbusiso", "Andile", "Busisiwe",
]

LAST_NAMES = [
    "Mokoena", "Dlamini", "Nkosi", "Khumalo", "Mahlangu", "Sithole", "Zulu",
    "Mbeki", "van der Merwe", "Botha", "Pretorius", "Naidoo", "Govender",
    "Mthembu", "Ndlovu", "Tshabalala", "Molefe", "Mokwena", "Mngomezulu", "Fourie",
]

MERCHANTS = {
    "Grocery": ["Pick n Pay", "Checkers", "Woolworths", "Shoprite", "Spar"],
    "Fuel": ["Engen", "Sasol", "Shell SA", "BP Express"],
    "Electronics": ["Incredible Connection", "HiFi Corp", "Game"],
    "Online Retail": ["Takealot", "Superbalist", "Makro Online"],
    "Restaurant": ["Nando's", "Steers", "Mugg & Bean", "KFC SA"],
    "Airtime & Data": ["Vodacom", "MTN", "Cell C", "Telkom"],
    "Clothing": ["Mr Price", "Edgars", "Truworths", "Ackermans"],
    "Bills & Insurance": ["DSTV", "Discovery", "Old Mutual", "Sanlam"],
    "ATM Withdrawal": [
        "ATM - FNB", "ATM - Standard Bank", "ATM - Absa",
        "ATM - Nedbank", "ATM - Capitec",
    ],
}

# Typical spend ranges per category, in ZAR - keeps "normal" traffic realistic
# and gives the fraud scorer something sensible to compare against.
CATEGORY_RANGES = {
    "Grocery": (50, 2500),
    "Fuel": (200, 1500),
    "Electronics": (300, 25000),
    "Online Retail": (100, 8000),
    "Restaurant": (60, 900),
    "Airtime & Data": (10, 500),
    "Clothing": (150, 4000),
    "Bills & Insurance": (200, 5000),
    "ATM Withdrawal": (100, 5000),
}


def generate_account_id() -> str:
    return f"ZA-{random.randint(10000000, 99999999)}"


def generate_account_holder() -> str:
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def random_city() -> dict:
    return random.choice(CITIES)


def random_merchant() -> tuple[str, str]:
    category = random.choice(list(MERCHANTS.keys()))
    merchant = random.choice(MERCHANTS[category])
    return merchant, category


def build_normal_transaction(account_id=None, account_holder=None, home_city=None) -> dict:
    """Builds a realistic, non-fraudulent transaction."""
    merchant, category = random_merchant()
    low, high = CATEGORY_RANGES[category]
    amount = round(random.uniform(low, high), 2)
    city = home_city or random_city()

    return {
        "transaction_id": str(uuid.uuid4()),
        "account_id": account_id or generate_account_id(),
        "account_holder": account_holder or generate_account_holder(),
        "amount": amount,
        "currency": "ZAR",
        "merchant_name": merchant,
        "merchant_category": category,
        "city": city["city"],
        "province": city["province"],
        "transaction_type": (
            "withdrawal" if category == "ATM Withdrawal" else random.choice(["purchase", "payment"])
        ),
        "channel": (
            "ATM" if category == "ATM Withdrawal" else random.choice(["POS", "Online", "Mobile App"])
        ),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "is_fraud_simulated": False,
    }


def build_fraud_transaction(account_id=None, account_holder=None, home_city=None) -> dict:
    """
    Builds a transaction mimicking one real-world fraud pattern:
      - amount_spike:        spend far above the category norm
      - odd_hour:             activity between 01:00-04:59
      - impossible_travel:    a city far from the account's home city
      - card_testing:         a small, near-identical online charge
    """
    pattern = random.choice(["amount_spike", "odd_hour", "impossible_travel", "card_testing"])
    txn = build_normal_transaction(account_id, account_holder, home_city)

    if pattern == "amount_spike":
        category = txn["merchant_category"]
        low, high = CATEGORY_RANGES[category]
        txn["amount"] = round(high * random.uniform(5, 20), 2)

    elif pattern == "odd_hour":
        odd_hour = random.choice([1, 2, 3, 4])
        ts = datetime.now(timezone.utc).replace(hour=odd_hour, minute=random.randint(0, 59))
        txn["timestamp"] = ts.isoformat()

    elif pattern == "impossible_travel":
        home_name = (home_city or {}).get("city")
        other_cities = [c for c in CITIES if c["city"] != home_name]
        far_city = random.choice(other_cities) if other_cities else random_city()
        txn["city"] = far_city["city"]
        txn["province"] = far_city["province"]

    elif pattern == "card_testing":
        txn["amount"] = round(random.uniform(1, 50), 2)
        txn["channel"] = "Online"
        txn["merchant_category"] = "Online Retail"
        txn["merchant_name"] = "Online Retail"

    txn["is_fraud_simulated"] = True
    txn["fraud_pattern"] = pattern
    return txn


def delivery_report(err, msg):
    if err is not None:
        print(f"[producer] Delivery failed: {err}")


def run():
    producer = Producer({"bootstrap.servers": config.KAFKA_BOOTSTRAP_SERVERS})
    interval = 1.0 / max(config.TRANSACTIONS_PER_SECOND, 0.1)

    # A pool of recurring accounts gives the fraud consumer transaction
    # history to compare against (velocity, home city, etc.) rather than
    # every transaction belonging to a brand new, history-less account.
    accounts = [
        {
            "account_id": generate_account_id(),
            "account_holder": generate_account_holder(),
            "home_city": random_city(),
        }
        for _ in range(25)
    ]

    print(
        f"[producer] Streaming to topic '{config.KAFKA_TOPIC}' on "
        f"{config.KAFKA_BOOTSTRAP_SERVERS} (~{config.TRANSACTIONS_PER_SECOND}/s, "
        f"fraud injection rate {config.FRAUD_INJECTION_RATE:.0%})"
    )

    try:
        while True:
            acct = random.choice(accounts)
            if random.random() < config.FRAUD_INJECTION_RATE:
                txn = build_fraud_transaction(acct["account_id"], acct["account_holder"], acct["home_city"])
            else:
                txn = build_normal_transaction(acct["account_id"], acct["account_holder"], acct["home_city"])

            producer.produce(
                config.KAFKA_TOPIC,
                key=txn["account_id"],
                value=json.dumps(txn).encode("utf-8"),
                callback=delivery_report,
            )
            producer.poll(0)
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n[producer] Stopped by user.")
    finally:
        producer.flush()


if __name__ == "__main__":
    run()
