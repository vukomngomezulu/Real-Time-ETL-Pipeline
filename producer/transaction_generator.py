import random
import time
from faker import Faker
from datetime import datetime

fake = Faker()

LOCATIONS = ["Johannesburg", "Cape Town", "Durban", "Pretoria", "Mpumalanga"]
MERCHANTS = ["Takealot", "Checkers", "Pick n Pay", "Amazon", "Uber", "KFC"]

def generate_transaction():
    user_id = random.randint(1000, 1100)

    # 10% chance of fraud-like transaction
    if random.random() < 0.1:
        amount = round(random.uniform(10000, 50000), 2)  # suspicious
    else:
        amount = round(random.uniform(10, 2000), 2)  # normal

    transaction = {
        "user_id": user_id,
        "amount": amount,
        "timestamp": datetime.now().isoformat(),
        "location": random.choice(LOCATIONS),
        "merchant": random.choice(MERCHANTS)
    }

    return transaction


def stream_transactions():
    while True:
        transaction = generate_transaction()
        print(transaction)  # later this goes to Kafka
        time.sleep(1)  # simulate real-time flow


if __name__ == "__main__":
    stream_transactions()