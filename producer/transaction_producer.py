from kafka import KafkaProducer
import json
import time
import random
from datetime import datetime

LOCATIONS = ["Johannesburg", "Cape Town", "Durban", "Pretoria", "Richard's Bay", "Esikhawini", "Port Elizabeth", "Ermelo", "Polokwane", "Bloemfontein", "East London", "Pietermaritzburg", "Nelspruit"]
MERCHANTS = ["Takealot", "Checkers", "Pick n Pay", "Shoprite", "Woolworths", "KFC", "McDonald's", "Spar", "Nando's", "Clicks", "Dis-Chem", "Makro", "Game", "Edgars"]

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def generate_transaction():
    return {
        "user_id": random.randint(10000, 11000),
        "amount": round(random.uniform(100, 50000), 2),
        "timestamp": datetime.now().isoformat(),
        "location": random.choice(LOCATIONS),
        "merchant": random.choice(MERCHANTS)
    }

while True:
    transaction = generate_transaction()
    producer.send("transactions", value=transaction)
    print("Sent:", transaction)
    time.sleep(1)