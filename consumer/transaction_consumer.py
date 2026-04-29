from kafka import KafkaConsumer
import json
import psycopg2

consumer = KafkaConsumer(
    'transactions',
    bootstrap_servers='localhost:9092',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

# fraud rules
def is_fraud(transaction):
    if transaction["amount"] > 10000:
        return True
    if transaction["location"] == "Unknown":
        return True
    return False

def transform(transaction):
    transaction["amount_category"] = (
        "HIGH" if transaction["amount"] > 10000 else "LOW"
    )
    return transaction

print("Listening for transactions...\n")

conn = psycopg2.connect(
    dbname="fintech",
    user="admin",
    password="admin",
    host="localhost",
    port="5432"
)
cursor = conn.cursor()

for message in consumer:
    transaction = message.value

    transformed = transform(transaction)

    fraud = is_fraud(transformed)

    cursor.execute(
        """
        INSERT INTO transactions (user_id, amount, timestamp, location, merchant, is_fraud)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            transformed["user_id"],
            transformed["amount"],
            transformed["timestamp"],
            transformed["location"],
            transformed["merchant"],
            fraud
        )
    )
    conn.commit()

    
    print("Transaction:", transformed)

    if fraud:
        print(" FRAUD DETECTED:", transformed)
    else:
        print(" Legit transaction")

    print("-" * 50)
