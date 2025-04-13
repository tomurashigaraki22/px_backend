from flask import request, jsonify, render_template
from extensions.extensions import app, db_connection as get_db_connection, mail
from flask_mail import Message
import jwt
import os
from dotenv import load_dotenv
import time
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
        print("Sending login notification now")
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

def send_admin_login_notification():
    try:
        now = datetime.now()
        msg = Message(
            "Admin Panel Login Alert - PX Backend",
            recipients=["devtomiwa9@gmail.com"]
        )
        msg.html = render_template(
            'admin_login_notification.html',
            login_date=now.strftime("%Y-%m-%d"),
            login_time=now.strftime("%H:%M:%S"),
            ip_address=request.remote_addr
        )
        mail.send(msg)
    except Exception as e:
        print(f"Error sending admin login notification: {str(e)}")

def send_withdrawal_request_notification():
    try:
        msg = Message(
            "New Withdrawal Request - PX Backend",
            recipients=["devtomiwa9@gmail.com"]
        )
        msg.html = render_template(
            'withdrawal_notification.html',
            request_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        mail.send(msg)
    except Exception as e:
        print(f"Error sending withdrawal notification: {str(e)}")

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
        send_login_notification(user)
        
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
        
        send_welcome_email(new_user)
        
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

def get_order_history(user_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT * FROM order_history 
            WHERE user_id = %s 
            ORDER BY created_at DESC
        """, (user_id,))
        
        orders = cur.fetchall()
        
        # Format orders with specific keys
        formatted_orders = []
        for order in orders:
            formatted_orders.append({
                'id': order['id'],
                'user_id': order['user_id'],
                'order_id': order['order_id'],
                'service_name': order['service_name'],
                'link': order['link'],
                'amount': float(order['amount']),
                'status': order['status'],
                'created_at': order['created_at'].strftime("%Y-%m-%d %H:%M:%S"),
                'updated_at': order['updated_at'].strftime("%Y-%m-%d %H:%M:%S")
            })
        
        return jsonify({
            "status": "success",
            "orders": formatted_orders
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if conn:
            conn.close()

def create_order(data):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if order_id already exists
        cur.execute("SELECT id FROM order_history WHERE order_id = %s", (data['order_id'],))
        if cur.fetchone():
            raise Exception("Order ID already exists")
        
        # Validate status
        valid_statuses = ['pending', 'completing', 'completed', 'cancelled']
        if data['status'] not in valid_statuses:
            raise Exception(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        
        # Check user balance if status requires payment
        if data['status'] in ['pending', 'completed', 'completing']:
            cur.execute("SELECT balance FROM users WHERE id = %s", (data['user_id'],))
            user = cur.fetchone()
            if not user:
                raise Exception("User not found")
                
            if float(user['balance']) < float(data['amount']):
                print(f"USER: {float(user['balance'])} {float(data['amount'])}")
                raise Exception("Insufficient balance")
            
            # Deduct balance
            new_balance = float(user['balance']) - float(data['amount'])
            cur.execute("UPDATE users SET balance = %s WHERE id = %s", (new_balance, data['user_id']))
            
            # Record transaction
            cur.execute("""
                INSERT INTO transactions 
                (user_id, type, amount, previous_balance, new_balance, status, description)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                data['user_id'],
                'debit',
                float(data['amount']),
                float(user['balance']),
                new_balance,
                'completed',
                f"Payment for order {data['order_id']}: {data['service_name']}"
            ))
            
        # Insert new order
        cur.execute("""
            INSERT INTO order_history 
            (user_id, order_id, service_name, link, amount, status, agent_id, commission)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data['user_id'],
            data['order_id'],
            data['service_name'],
            data['link'],
            float(data['amount']),
            data['status'],
            data.get('agentId', None),
            float(10)
        ))
        
        conn.commit()
        
        # Get the created order
        cur.execute("SELECT * FROM order_history WHERE order_id = %s", (data['order_id'],))
        order = cur.fetchone()
        
        return jsonify({
            "status": "success",
            "message": "Order created successfully",
            "order": {
                'id': order['id'],
                'user_id': order['user_id'],
                'order_id': order['order_id'],
                'service_name': order['service_name'],
                'link': order['link'],
                'amount': float(order['amount']),
                'status': order['status'],
                'created_at': order['created_at'].strftime("%Y-%m-%d %H:%M:%S"),
                'updated_at': order['updated_at'].strftime("%Y-%m-%d %H:%M:%S")
            }
        })
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if conn:
            conn.close()


def agent_signup():
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({"message": "No data provided", "status": 400}), 400
            
        email = data.get('email')
        password = data.get('password')
        
        if not all([email, password]):
            return jsonify({
                "message": "Email and password are required",
                "status": 400
            }), 400
        
        # First, try to login to verify user exists
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if user exists
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        
        if not user:
            return jsonify({
                "status": "error",
                "message": "User does not exist. Please sign up as a regular user first."
            }), 404
        
        # Verify password (plain text comparison)
        if user['password'] != password:
            return jsonify({
                "status": "error",
                "message": "Invalid credentials"
            }), 401
        
        # Check if already an agent
        if user['is_agent']:
            return jsonify({
                "status": "error",
                "message": "User is already registered as an agent"
            }), 400
        
        # Generate agent_id from email (remove @domain.com)
        agent_id = email.split('@')[0]
        
        # Update user as agent
        cur.execute("""
            UPDATE users 
            SET is_agent = TRUE, 
                agent_id = %s, 
                agent_password = %s
            WHERE id = %s
        """, (agent_id, password, user['id']))
        
        conn.commit()
        
        # Get updated user info
        cur.execute("SELECT id, username, email, balance, agent_id, is_agent FROM users WHERE id = %s", (user['id'],))
        updated_user = cur.fetchone()
        
        return jsonify({
            "status": "success",
            "message": "Successfully registered as an agent",
            "user": {
                "id": updated_user['id'],
                "username": updated_user['username'],
                "email": updated_user['email'],
                "balance": float(updated_user['balance']),
                "agent_id": updated_user['agent_id'],
                "is_agent": updated_user['is_agent']
            }
        })
        
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

def agent_login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "No data provided", "status": 400}), 400
            
        agent_id = data.get('agent_id')
        password = data.get('password')
        
        if not all([agent_id, password]):
            return jsonify({
                "message": "Agent ID and password are required",
                "status": 400
            }), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if agent exists and credentials are correct
        cur.execute("""
            SELECT u.*, ai.* 
            FROM users u 
            LEFT JOIN agent_info ai ON u.id = ai.agent_user_id 
            WHERE u.agent_id = %s AND u.agent_password = %s AND u.is_agent = TRUE
        """, (agent_id, password))
        
        agent = cur.fetchone()
        if not agent:
            return jsonify({
                "status": "error",
                "message": "Invalid agent credentials"
            }), 401
            
        # Check subscription status
        subscription_valid = False
        if agent['is_paid'] and agent['subscription_end_date']:
            if datetime.now() < agent['subscription_end_date']:
                subscription_valid = True
        
        return jsonify({
            "status": "success",
            "message": "Agent login successful",
            "agent": {
                "id": agent['id'],
                "username": agent['username'],
                "email": agent['email'],
                "agent_id": agent['agent_id'],
                "commission_rate": float(agent['commission_rate']) if agent['commission_rate'] else None,
                "subscription_valid": subscription_valid,
                "subscription_end_date": agent['subscription_end_date'].strftime("%Y-%m-%d %H:%M:%S") if agent['subscription_end_date'] else None,
                "total_earnings": float(agent['total_earnings']) if agent['total_earnings'] else 0.00,
                "pending_earnings": float(agent['pending_earnings']) if agent['pending_earnings'] else 0.00
            }
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if conn:
            conn.close()

def check_agent_subscription():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "No data provided", "status": 400}), 400
            
        agent_id = data.get('agent_id')
        
        if not agent_id:
            return jsonify({
                "message": "Agent ID is required",
                "status": 400
            }), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT * FROM agent_info 
            WHERE agent_id = %s
        """, (agent_id,))
        
        agent_info = cur.fetchone()
        
        if not agent_info:
            return jsonify({
                "status": "error",
                "message": "Agent not found"
            }), 404
            
        subscription_status = {
            "is_paid": agent_info['is_paid'],
            "subscription_type": agent_info['subscription_type'],
            "commission_rate": float(agent_info['commission_rate']),
            "subscription_start": agent_info['subscription_start_date'].strftime("%Y-%m-%d %H:%M:%S") if agent_info['subscription_start_date'] else None,
            "subscription_end": agent_info['subscription_end_date'].strftime("%Y-%m-%d %H:%M:%S") if agent_info['subscription_end_date'] else None,
            "is_active": False,
            "days_remaining": 0
        }
        
        if agent_info['is_paid'] and agent_info['subscription_end_date']:
            now = datetime.now()
            if now < agent_info['subscription_end_date']:
                subscription_status["is_active"] = True
                days_remaining = (agent_info['subscription_end_date'] - now).days
                subscription_status["days_remaining"] = days_remaining
        
        return jsonify({
            "status": "success",
            "subscription": subscription_status
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if conn:
            conn.close()


def subscribe_agent():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "No data provided", "status": 400}), 400
            
        agent_id = data.get('agent_id')
        subscription_type = data.get('subscription_type')
        
        if not all([agent_id, subscription_type]):
            return jsonify({
                "message": "Agent ID and subscription type are required",
                "status": 400
            }), 400
            
        if subscription_type not in ['basic', 'premium']:
            return jsonify({
                "message": "Invalid subscription type. Must be 'basic' or 'premium'",
                "status": 400
            }), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get subscription details based on type
        subscription_details = {
            'basic': {'amount': 5000.00, 'commission_rate': 5.00},
            'premium': {'amount': 48000.00, 'commission_rate': 10.00}
        }[subscription_type]
        
        # Get agent user details
        cur.execute("SELECT id FROM users WHERE agent_id = %s AND is_agent = TRUE", (agent_id,))
        agent = cur.fetchone()
        if not agent:
            return jsonify({
                "status": "error",
                "message": "Agent not found"
            }), 404
            
        # Check if agent already has subscription
        cur.execute("SELECT * FROM agent_info WHERE agent_id = %s", (agent_id,))
        existing_subscription = cur.fetchone()
        
        subscription_start = datetime.now()
        subscription_end = subscription_start.replace(year=subscription_start.year + 1)
        
        if existing_subscription:
            # Update existing subscription
            cur.execute("""
                UPDATE agent_info 
                SET subscription_type = %s,
                    commission_rate = %s,
                    subscription_amount = %s,
                    is_paid = TRUE,
                    subscription_start_date = %s,
                    subscription_end_date = %s,
                    paid_at = NOW()
                WHERE agent_id = %s
            """, (
                subscription_type,
                subscription_details['commission_rate'],
                subscription_details['amount'],
                subscription_start,
                subscription_end,
                agent_id
            ))
        else:
            # Create new subscription
            cur.execute("""
                INSERT INTO agent_info 
                (agent_id, agent_user_id, subscription_type, commission_rate, 
                subscription_amount, is_paid, subscription_start_date, 
                subscription_end_date, paid_at)
                VALUES (%s, %s, %s, %s, %s, TRUE, %s, %s, NOW())
            """, (
                agent_id,
                agent['id'],
                subscription_type,
                subscription_details['commission_rate'],
                subscription_details['amount'],
                subscription_start,
                subscription_end
            ))
        
        conn.commit()
        
        return jsonify({
            "status": "success",
            "message": "Subscription activated successfully",
            "subscription": {
                "type": subscription_type,
                "amount": subscription_details['amount'],
                "commission_rate": subscription_details['commission_rate'],
                "start_date": subscription_start.strftime("%Y-%m-%d %H:%M:%S"),
                "end_date": subscription_end.strftime("%Y-%m-%d %H:%M:%S")
            }
        }), 200
        
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

def check_agent_id(agent_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT agent_id, username, is_agent 
            FROM users 
            WHERE agent_id = %s AND is_agent = TRUE
        """, (agent_id,))
        
        agent = cur.fetchone()
        
        if not agent:
            return jsonify({
                "status": "error",
                "message": "Agent ID not found",
                "exists": False
            }), 404
            
        return jsonify({
            "status": "success",
            "message": "Agent ID exists",
            "exists": True,
            "agent": {
                "agent_id": agent['agent_id'],
                "username": agent['username']
            }
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if conn:
            conn.close()


def get_agent_orders(agent_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get count of orders for this agent
        cur.execute("""
            SELECT COUNT(*) as order_count 
            FROM order_history 
            WHERE agent_id = %s
        """, (agent_id,))
        
        count_result = cur.fetchone()
        order_count = count_result['order_count'] if count_result else 0
        
        # Get order details
        cur.execute("""
            SELECT order_id, amount, created_at
            FROM order_history 
            WHERE agent_id = %s 
            ORDER BY created_at DESC
        """, (agent_id,))
        
        orders = cur.fetchall()
        
        order_details = [{
            'order_id': order['order_id'],
            'amount': float(order['amount']),
            'date': order['created_at'].strftime("%Y-%m-%d %H:%M:%S")
        } for order in orders]
        
        return jsonify({
            "status": "success",
            "total_orders": order_count,
            "orders": order_details
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if conn:
            conn.close()

def get_agent_order_details(agent_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT oh.*, u.username as customer_name
            FROM order_history oh
            LEFT JOIN users u ON oh.user_id = u.id
            WHERE oh.agent_id = %s 
            ORDER BY oh.created_at DESC
        """, (agent_id,))
        
        orders = cur.fetchall()
        
        detailed_orders = [{
            'id': order['id'],
            'order_id': order['order_id'],
            'customer_name': order['customer_name'],
            'user_id': order['user_id'],
            'service_name': order['service_name'],
            'link': order['link'],
            'amount': float(order['amount']),
            'status': order['status'],
            'is_paid_agent': order['is_paid_agent'],
            'commission': float(order['commission']) if order['commission'] else 0.00,
            'created_at': order['created_at'].strftime("%Y-%m-%d %H:%M:%S"),
            'updated_at': order['updated_at'].strftime("%Y-%m-%d %H:%M:%S")
        } for order in orders]
        
        return jsonify({
            "status": "success",
            "total_orders": len(detailed_orders),
            "orders": detailed_orders
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if conn:
            conn.close()

def get_agent_withdrawal_details(agent_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get all completed orders where commission is pending
        cur.execute("""
            SELECT oh.order_id, oh.amount, oh.commission
            FROM order_history oh
            WHERE oh.agent_id = %s 
            AND oh.is_paid_agent = 'pending'
        """, (agent_id,))
        
        completed_orders = cur.fetchall()
        print(f"Completed orders: {completed_orders}")
        
        # Calculate available balance
        available_balance = 0
        for order in completed_orders:
            commission = (float(order['commission']) * float(order['amount'])) / 100
            available_balance += commission
        
        # Get withdrawal history
        cur.execute("""
            SELECT aw.*, GROUP_CONCAT(oh.order_id) as order_ids
            FROM agent_withdrawals aw
            LEFT JOIN order_history oh ON FIND_IN_SET(oh.order_id, aw.order_ids)
            WHERE aw.agent_id = %s
            GROUP BY aw.id
            ORDER BY aw.created_at DESC
        """, (agent_id,))
        
        withdrawals = cur.fetchall()
        
        return jsonify({
            "status": "success",
            "availableBalance": float(available_balance),
            "withdrawals": [{
                'id': w['id'],
                'amount': float(w['amount']),
                'status': w['status'],
                'transaction_reference': w['transaction_reference'],
                'created_at': w['created_at'].strftime("%Y-%m-%d %H:%M:%S"),
                'order_ids': w['order_ids'].split(',') if w['order_ids'] else []
            } for w in withdrawals]
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if conn:
            conn.close()

def create_withdrawal_request(data):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        agent_id = data['agent_id']
        amount = float(data['amount'])
        order_ids = data['order_ids']
        bank_name = data['bank_name']
        account_number = data['account_number']
        print(f"order:  {order_ids}")
        
        # Verify orders and calculate total available
        total_available = 0
        for order_id in order_ids:
            print(f"ORDER ID: {order_id}")
            cur.execute("""
                SELECT oh.amount, oh.commission
                FROM order_history oh
                WHERE oh.order_id = %s 
                AND oh.agent_id = %s
                AND oh.is_paid_agent = 'pending'
            """, (order_id, agent_id))
            
            order = cur.fetchone()
            print(f"ORDER: {order}")
            if order:
                commission = (float(order['commission']) * float(order['amount'])) / 100
                total_available += commission
        
        if amount > total_available:
            print(f"Amount: {amount}, Total available: {total_available}")
            raise Exception("Insufficient balance for withdrawal")
        
        # Create withdrawal record
        transaction_reference = f"WD-{int(time.time())}"
        cur.execute("""
            INSERT INTO agent_withdrawals 
            (agent_id, amount, order_ids, transaction_reference, bank_name, account_number)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (agent_id, amount, ','.join(order_ids), transaction_reference, bank_name, account_number))
        
        # Update orders to processing status
        for order_id in order_ids:
            cur.execute("""
                UPDATE order_history 
                SET is_paid_agent = 'processing'
                WHERE order_id = %s AND agent_id = %s
            """, (order_id, agent_id))
        
        conn.commit()
        send_withdrawal_request_notification()
        
        return jsonify({
            "status": "success",
            "message": "Withdrawal request created successfully",
            "transaction_reference": transaction_reference
        })
        
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    finally:
        if conn:
            conn.close()