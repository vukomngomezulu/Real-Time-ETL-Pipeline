from flask import Flask, render_template, jsonify
import psycopg2
from datetime import datetime, timedelta
import json

app = Flask(__name__)

# Database connection
def get_db_connection():
    conn = psycopg2.connect(
        dbname="fintech",
        user="admin",
        password="admin",
        host="localhost",
        port="5432"
    )
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats')
def get_stats():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get last hour of data
        one_hour_ago = datetime.now() - timedelta(hours=1)
        
        # Total transactions
        cursor.execute(
            "SELECT COUNT(*) FROM transactions WHERE timestamp > %s",
            (one_hour_ago,)
        )
        total_transactions = cursor.fetchone()[0]
        
        # Fraud count
        cursor.execute(
            "SELECT COUNT(*) FROM transactions WHERE timestamp > %s AND is_fraud = true",
            (one_hour_ago,)
        )
        fraud_count = cursor.fetchone()[0]
        
        # Fraud rate
        fraud_rate = (fraud_count / total_transactions * 100) if total_transactions > 0 else 0
        
        # Total amount transacted
        cursor.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE timestamp > %s",
            (one_hour_ago,)
        )
        total_amount = float(cursor.fetchone()[0])
        
        # Fraudulent amount
        cursor.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE timestamp > %s AND is_fraud = true",
            (one_hour_ago,)
        )
        fraud_amount = float(cursor.fetchone()[0])
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'total_transactions': total_transactions,
            'fraud_count': fraud_count,
            'fraud_rate': round(fraud_rate, 2),
            'total_amount': round(total_amount, 2),
            'fraud_amount': round(fraud_amount, 2)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recent-transactions')
def get_recent_transactions():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT user_id, amount, timestamp, location, merchant, is_fraud, amount_category
            FROM transactions
            ORDER BY timestamp DESC
            LIMIT 50
            """
        )
        
        columns = ['user_id', 'amount', 'timestamp', 'location', 'merchant', 'is_fraud', 'amount_category']
        transactions = []
        
        for row in cursor.fetchall():
            transactions.append(dict(zip(columns, row)))
        
        cursor.close()
        conn.close()
        
        return jsonify(transactions)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/fraud-timeline')
def get_fraud_timeline():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get hourly fraud count for last 24 hours
        cursor.execute(
            """
            SELECT 
                DATE_TRUNC('hour', timestamp) as hour,
                COUNT(*) as total,
                SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) as fraud_count
            FROM transactions
            WHERE timestamp > NOW() - INTERVAL '24 hours'
            GROUP BY DATE_TRUNC('hour', timestamp)
            ORDER BY hour
            """
        )
        
        timeline = []
        for row in cursor.fetchall():
            timeline.append({
                'time': row[0].isoformat() if row[0] else None,
                'total': row[1],
                'fraud': row[2]
            })
        
        cursor.close()
        conn.close()
        
        return jsonify(timeline)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/top-merchants')
def get_top_merchants():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT merchant, COUNT(*) as count, SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) as fraud_count
            FROM transactions
            WHERE timestamp > NOW() - INTERVAL '24 hours'
            GROUP BY merchant
            ORDER BY count DESC
            LIMIT 10
            """
        )
        
        merchants = []
        for row in cursor.fetchall():
            merchants.append({
                'merchant': row[0],
                'count': row[1],
                'fraud_count': row[2]
            })
        
        cursor.close()
        conn.close()
        
        return jsonify(merchants)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/amount-distribution')
def get_amount_distribution():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            """
            SELECT amount_category, COUNT(*) as count, SUM(CASE WHEN is_fraud THEN 1 ELSE 0 END) as fraud_count
            FROM transactions
            WHERE timestamp > NOW() - INTERVAL '24 hours'
            GROUP BY amount_category
            """
        )
        
        distribution = {}
        for row in cursor.fetchall():
            distribution[row[0]] = {'count': row[1], 'fraud_count': row[2]}
        
        cursor.close()
        conn.close()
        
        return jsonify(distribution)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
