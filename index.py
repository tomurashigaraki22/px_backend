from flask import request, jsonify
from flask_cors import CORS
import pymysql
from dotenv import load_dotenv
from extensions.extensions import app, db_connection as get_db_connection
from extensions.dbschemas import init_database
from functions.auth import *

# Load environment variables
load_dotenv()

# Initialize database tables
try:
    conn = get_db_connection()
    init_database(conn)
    conn.close()
    print("Database tables initialized successfully")
except Exception as e:
    print(f"Error initializing database tables: {e}")

@app.route('/')
def home():
    return jsonify({
        "status": "success",
        "message": "Welcome to PX Backend API"
    })

@app.route('/test-connection')
def test_connection():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute('SELECT 1')
            result = cursor.fetchone()
        conn.close()
        return jsonify({
            "status": "success",
            "message": "Database connection successful"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/auth/login", methods=["GET", "POST"])
def loginNow():
    return login()

@app.route("/auth/signup", methods=["GET", "POST"])
def signupNow():
    return signup()

@app.route('/show/<tablename>')
def show_table(tablename):
    # List of allowed tables for querying
    allowed_tables = ['users']
    
    if tablename not in allowed_tables:
        return jsonify({
            "status": "error",
            "message": "Invalid table name"
        }), 400
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {tablename} ORDER BY id")
            results = cursor.fetchall()
        conn.close()
        
        return jsonify({
            "status": "success",
            "data": results
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/balance/update', methods=['POST'])
def update_user_balance():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "No data provided", "status": 400}), 400
            
        user_id = data.get('user_id')
        amount = data.get('amount')
        transaction_type = data.get('type')
        
        if not all([user_id, amount, transaction_type]):
            print("Missing required fields: user_id, amount, and type")
            return jsonify({
                "message": "Missing required fields: user_id, amount, and type",
                "status": 400
            }), 400
            
        return update_balance(user_id, float(amount), transaction_type)
        
    except Exception as e:
        return jsonify({"message": str(e), "status": 500}), 500

@app.route('/balance/set', methods=['POST'])
def set_user_balance():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "No data provided", "status": 400}), 400
            
        user_id = data.get('user_id')
        amount = data.get('amount')
        
        if not all([user_id, amount]):
            return jsonify({
                "message": "Missing required fields: user_id and amount",
                "status": 400
            }), 400
            
        return set_balance(user_id, float(amount))
        
    except Exception as e:
        return jsonify({"message": str(e), "status": 500}), 500

@app.route('/balance/get/<int:user_id>', methods=['GET'])
def get_user_balance(user_id):
    try:
        if not user_id:
            return jsonify({
                "message": "User ID is required",
                "status": 400
            }), 400
            
        return get_balance(user_id)
        
    except Exception as e:
        return jsonify({"message": str(e), "status": 500}), 500

@app.route('/transactions/<int:user_id>', methods=['GET'])
def get_transactions(user_id):
    try:
        if not user_id:
            return jsonify({
                "message": "User ID is required",
                "status": 400
            }), 400
            
        return get_user_transactions(user_id)
        
    except Exception as e:
        return jsonify({"message": str(e), "status": 500}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=1245)
