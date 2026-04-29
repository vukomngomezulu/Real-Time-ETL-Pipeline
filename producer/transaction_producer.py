from kafka import KafkaProducer
import json
import time
import random
from faker import Faker
from datetime import datetime

fake = Faker()

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def generate_transaction():
    return {
        "user_id": random.randint(1000, 1100),
        "amount": round(random.uniform(10, 50000), 2),
        "timestamp": datetime.now().isoformat(),
        "location": fake.city(),
        "merchant": fake.company()
    }

while True:
    transaction = generate_transaction()
    producer.send("transactions", value=transaction)
    print("Sent:", transaction)
    time.sleep(1)