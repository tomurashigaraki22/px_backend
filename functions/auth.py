from flask import request, jsonify, render_template
from extensions.extensions import app, db_connection as get_db_connection, mail
from flask_mail import Message
import jwt
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
JWT_SECRET = os.getenv('JWT_SECRET', 'your-secret-key-here')

def generate_token(user_data):
    return jwt.encode(
        {
            'user_id': user_data['id'],
            'username': user_data['username'],
            'email': user_data['email']
        },
        JWT_SECRET,
        algorithm='HS256'
    )

def send_welcome_email(user):
    try:
        print("Sending welcome mail now")
        msg = Message(
            "Welcome to PX Backend!",
            recipients=[user['email']]
        )
        msg.html = render_template(
            'welcome_email.html',
            username=user['username'],
            email=user['email']
        )
        mail.send(msg)
        print("welcome mail sent")
    except Exception as e:
        print(f"Error sending welcome email: {str(e)}")

def send_login_notification(user):
    try:
        now = datetime.now()
        msg = Message(
            "New Login Detected - PX Backend",
            recipients=[user['email']]
        )
        msg.html = render_template(
            'login_notification.html',
            username=user['username'],
            user_id=user['id'],
            login_date=now.strftime("%Y-%m-%d"),
            login_time=now.strftime("%H:%M:%S"),
            ip_address=request.remote_addr
        )
        mail.send(msg)
    except Exception as e:
        print(f"Error sending login notification: {str(e)}")

def login():
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        data = request.get_json()
        if data is None:
            return jsonify({"message": "Data is empty", "status": 404}), 404

        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({"message": "Email and password are required", "status": 404}), 404

        cur.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))

        user = cur.fetchone()
        if user is None:
            return jsonify({"message": "Invalid email or password", "status": 404}), 404
        
        # Generate token with user data
        token = generate_token(user)
        
        # Send login notification
        # send_login_notification(user)
        
        return jsonify({
            "message": "Login successful",
            "status": 200,
            "token": token,
            "user": {
                "id": user['id'],
                "username": user['username'],
                "email": user['email']
            }
        }), 200
    except Exception as e:
        return jsonify({"message": str(e), "status": 500}), 500

def signup():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        data = request.get_json()
        if data is None:
            return jsonify({"message": "Data is empty", "status": 404}), 404
        email = data.get("email")
        password = data.get("password")
        username = data.get("username")
        if not email or not password or not username:
            return jsonify({"message": "Email, password, and username are required", "status": 404}), 404

        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        if user:
            return jsonify({"message": "Email already exists", "status": 404}), 404

        cur.execute("INSERT INTO users (email, password, username) VALUES (%s, %s, %s)", (email, password, username))
        conn.commit()
        
        # Get the newly created user
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        new_user = cur.fetchone()
        
        # Generate token for new user
        token = generate_token(new_user)
        
        # Send welcome email
        # send_welcome_email(new_user)
        
        return jsonify({
            "message": "Signup successful",
            "status": 200,
            "token": token,
            "user": {
                "id": new_user['id'],
                "username": new_user['username'],
                "email": new_user['email']
            }
        }), 200
    except Exception as e:
        return jsonify({"message": str(e), "status": 500}), 500


def update_balance(user_id, amount, transaction_type):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # First get current balance
        cur.execute("SELECT balance FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        
        if not user:
            raise Exception("User not found")
            
        current_balance = float(user['balance'])
        new_balance = current_balance
        
        if transaction_type.lower() == 'credit':
            new_balance = current_balance + amount
        elif transaction_type.lower() == 'debit':
            if current_balance < amount:
                raise Exception("Insufficient balance")
            new_balance = current_balance - amount
        else:
            raise Exception("Invalid transaction type")
            
        # Update the balance
        cur.execute("UPDATE users SET balance = %s WHERE id = %s", (new_balance, user_id))
        
        # Record the transaction
        cur.execute("""
            INSERT INTO transactions 
            (user_id, type, amount, previous_balance, new_balance, status, description)
            VALUES (%s, %s, %s, %s, %s, 'completed', %s)
        """, (
            user_id, 
            transaction_type.lower(), 
            amount, 
            current_balance, 
            new_balance,
            f"{transaction_type.capitalize()} transaction of {amount}"
        ))
        
        conn.commit()
        
        return jsonify({
            "status": "success",
            "message": f"Balance {transaction_type}ed successfully",
            "new_balance": new_balance
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if conn:
            conn.close()

def set_balance(user_id, amount):
    """
    Set user balance to a specific amount
    Args:
        user_id (int): User ID
        amount (int): New balance amount
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if user exists
        cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cur.fetchone():
            raise Exception("User not found")
            
        # Set the new balance
        cur.execute("UPDATE users SET balance = %s WHERE id = %s", (amount, user_id))
        conn.commit()
        
        return jsonify({
            "status": "success",
            "message": "Balance set successfully",
            "new_balance": amount
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if conn:
            conn.close()


def get_balance(user_id):
    """
    Get user's current balance
    Args:
        user_id (int): User ID
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT balance FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        
        if not user:
            return jsonify({
                "status": "error",
                "message": "User not found"
            }), 404
            
        return jsonify({
            "status": "success",
            "balance": float(user['balance'])
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if conn:
            conn.close()

def get_user_transactions(user_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT * FROM transactions 
            WHERE user_id = %s 
            ORDER BY created_at DESC
        """, (user_id,))
        
        transactions = cur.fetchall()
        
        return jsonify({
            "status": "success",
            "transactions": transactions
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if conn:
            conn.close()
        