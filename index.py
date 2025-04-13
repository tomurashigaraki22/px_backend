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
    print(f"Error initializing database tables: {str(e)}")

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

@app.route("/auth/agent-signup", methods=["POST"])
def agentSignupNow():
    return agent_signup()

@app.route('/show/<tablename>')
def show_table(tablename):
    # List of allowed tables for querying
    allowed_tables = ['users', 'transactions', 'order_history', 'agent_info', 'withdrawn_orders', 'agent_withdrawals']
    
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
        # Skip processing for CORS preflight requests
        if request.method == 'OPTIONS':
            return '', 200
            
        data = request.get_json()
        if not data:
            return jsonify({"message": "No data provided", "status": 400}), 400
            
        user_id = data.get('user_id')
        amount = data.get('amount')
        transaction_type = data.get('type')
        
        if not all([user_id, amount, transaction_type]):
            print(f"Missing required fields: user_id, amount, and type: {user_id} {amount} {transaction_type}")
            return jsonify({
                "message": "Missing required fields: user_id, amount, and type",
                "status": 400
            }), 400
        
        # Add transaction reference check
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check for recent duplicate transaction within last 5 seconds
        cur.execute("""
            SELECT id FROM transactions 
            WHERE user_id = %s 
            AND amount = %s 
            AND type = %s 
            AND created_at >= NOW() - INTERVAL 5 SECOND
        """, (user_id, amount, transaction_type))
        
        if cur.fetchone():
            return jsonify({
                "status": "success",
                "message": "Transaction already processed"
            }), 200
            
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

@app.route('/orders/<int:user_id>', methods=['GET'])
def get_user_orders(user_id):
    try:
        if not user_id:
            return jsonify({
                "message": "User ID is required",
                "status": 400
            }), 400
            
        return get_order_history(user_id)
        
    except Exception as e:
        return jsonify({"message": str(e), "status": 500}), 500

@app.route('/test-mail', methods=["GET", "POST"])
def test_mail():
    try:
        msg = Message(
            "Welcome to PXSM",
            recipients=["devtomiwa9@gmail.com"]  # Replace with test email
        )
        msg.html = """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #4a5568;">Welcome to PXSM! 👋</h2>
            <p style="color: #718096;">This is a test email confirming that our mailing system is working correctly.</p>
            <div style="background-color: #f7fafc; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p style="color: #4a5568; margin: 0;">If you received this email, it means our email configuration is successful!</p>
            </div>
            <p style="color: #718096;">Best regards,<br>PXSM Team</p>
        </div>
        """
        mail.send(msg)
        return jsonify({
            "status": "success",
            "message": "Test email sent successfully"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/orders/create', methods=['POST'])
def create_new_order():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "No data provided", "status": 400}), 400
            
        required_fields = ['user_id', 'order_id', 'service_name', 'link', 'amount', 'status', 'agentId']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                "message": f"Missing required fields: {', '.join(missing_fields)}",
                "status": 400
            }), 400

        print(data['agentId'])
            
        return create_order(data)
        
    except Exception as e:
        return jsonify({"message": str(e), "status": 500}), 500

@app.route('/table/<tablename>')
def view_table(tablename):
    # List of allowed tables for querying
    allowed_tables = ['users', 'transactions', 'order_history', 'agent_info']
    
    if tablename not in allowed_tables:
        return jsonify({
            "status": "error",
            "message": "Invalid or unauthorized table name",
            "allowed_tables": allowed_tables
        }), 400
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Define sensitive fields to exclude per table
            sensitive_fields = {
                'users': [],
                'transactions': [],
                'order_history': []
            }
            
            # Get column names excluding sensitive fields
            cursor.execute(f"SHOW COLUMNS FROM {tablename}")
            columns = [column['Field'] for column in cursor.fetchall() 
                      if column['Field'] not in sensitive_fields.get(tablename, [])]
            
            # Build and execute the query
            fields = ", ".join(columns)
            cursor.execute(f"SELECT {fields} FROM {tablename} ORDER BY id DESC LIMIT 100")
            results = cursor.fetchall()
            
            return jsonify({
                "status": "success",
                "table": tablename,
                "columns": columns,
                "data": results,
                "count": len(results)
            })
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/auth/agent-login", methods=["POST"])
def agentLoginNow():
    return agent_login()

@app.route("/agent/subscription-status", methods=["POST"])
def checkAgentSubscription():
    return check_agent_subscription()

@app.route("/agent/subscribe", methods=["POST"])
def subscribeAgent():
    return subscribe_agent()

@app.route('/remove/<tablename>/<password>')
def remove_table(tablename, password):
    # List of allowed tables for deletion
    allowed_tables = ['users', 'agent_info']
    correct_password = 'bitcoin'
    
    if tablename not in allowed_tables:
        return jsonify({
            "status": "error",
            "message": "Invalid table name. Only users and agent_info tables can be cleared."
        }), 400
    
    if password != correct_password:
        return jsonify({
            "status": "error",
            "message": "Invalid password"
        }), 401
    
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Get record count before deletion
            cursor.execute(f"SELECT COUNT(*) as count FROM {tablename}")
            count = cursor.fetchone()['count']
            
            # Delete all records
            cursor.execute(f"DELETE FROM {tablename}")
            conn.commit()
            
            return jsonify({
                "status": "success",
                "message": f"Successfully cleared {tablename} table",
                "records_removed": count
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

@app.route("/check/<agent_id>", methods=["GET"])
def checkAgentId(agent_id):
    return check_agent_id(agent_id)

@app.route("/agent/orders", methods=["POST"])
def getAgentOrders():
    try:
        data = request.get_json()
        if not data or 'agent_id' not in data:
            return jsonify({
                "status": "error",
                "message": "Agent ID is required"
            }), 400
        return get_agent_orders(data['agent_id'])
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/agent/orders/<agent_id>", methods=["GET"])
def getAgentOrderDetails(agent_id):
    return get_agent_order_details(agent_id)

@app.route("/agent/withdrawal-details/<agent_id>", methods=["GET"])
def getAgentWithdrawalDetails(agent_id):
    return get_agent_withdrawal_details(agent_id)

@app.route("/agent/withdraw", methods=["POST"])
def createWithdrawalRequest():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "No data provided", "status": 400}), 400
            
        required_fields = ['agent_id', 'amount', 'order_ids', 'bank_name', 'account_number']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                "message": f"Missing required fields: {', '.join(missing_fields)}",
                "status": 400
            }), 400
            
        return create_withdrawal_request(data)
        
    except Exception as e:
        return jsonify({"message": str(e), "status": 500}), 500

# Add these new admin routes after your existing routes

@app.route("/admin/users", methods=["GET"])
def get_admin_users():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, username, email, balance, created_at, is_agent
            FROM users
            ORDER BY created_at DESC
        """)
        
        users = cur.fetchall()
        return jsonify([{
            'id': user['id'],
            'username': user['username'],
            'email': user['email'],
            'balance': float(user['balance']),
            'created_at': user['created_at'].strftime("%Y-%m-%d %H:%M:%S"),
            'is_agent': user['is_agent']
        } for user in users])
        
    except Exception as e:
        return jsonify({"message": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route("/admin/agents", methods=["GET"])
def get_admin_agents():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT u.id, u.username, u.email, ai.*
            FROM users u
            JOIN agent_info ai ON u.id = ai.agent_user_id
            WHERE u.is_agent = TRUE
            ORDER BY ai.created_at DESC
        """)
        
        agents = cur.fetchall()
        return jsonify([{
            'id': agent['id'],
            'username': agent['username'],
            'email': agent['email'],
            'agent_id': agent['agent_id'],
            'subscription_type': agent['subscription_type'],
            'total_earnings': float(agent['total_earnings']),
            'pending_earnings': float(agent['pending_earnings']),
            'created_at': agent['created_at'].strftime("%Y-%m-%d %H:%M:%S")
        } for agent in agents])
        
    except Exception as e:
        return jsonify({"message": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route("/admin/orders", methods=["GET"])
def get_admin_orders():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT oh.*, u.username
            FROM order_history oh
            LEFT JOIN users u ON oh.user_id = u.id
            ORDER BY oh.created_at DESC
        """)
        
        orders = cur.fetchall()
        return jsonify([{
            'id': order['id'],
            'order_id': order['order_id'],
            'username': order['username'],
            'service_name': order['service_name'],
            'amount': float(order['amount']),
            'status': order['status'],
            'created_at': order['created_at'].strftime("%Y-%m-%d %H:%M:%S")
        } for order in orders])
        
    except Exception as e:
        return jsonify({"message": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route("/admin/withdrawals", methods=["GET"])
def get_admin_withdrawals():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT aw.*, u.username
            FROM agent_withdrawals aw
            LEFT JOIN users u ON u.agent_id = aw.agent_id
            ORDER BY aw.created_at DESC
        """)
        
        withdrawals = cur.fetchall()
        return jsonify([{
            'id': w['id'],
            'agent_id': w['agent_id'],
            'username': w['username'],
            'amount': float(w['amount']),
            'status': w['status'],
            'bank_name': w['bank_name'],
            'account_number': w['account_number'],
            'created_at': w['created_at'].strftime("%Y-%m-%d %H:%M:%S")
        } for w in withdrawals])
        
    except Exception as e:
        return jsonify({"message": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route("/admin/metrics", methods=["GET"])
def get_admin_metrics():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get daily orders for the last 7 days
        cur.execute("""
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as count
            FROM order_history
            WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            GROUP BY DATE(created_at)
            ORDER BY date
        """)
        
        daily_orders = [{
            'date': row['date'].strftime("%Y-%m-%d"),
            'count': row['count']
        } for row in cur.fetchall()]
        
        # Get monthly revenue for the last 6 months
        cur.execute("""
            SELECT 
                DATE_FORMAT(created_at, '%Y-%m') as month,
                SUM(amount) as revenue
            FROM order_history
            WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
            GROUP BY DATE_FORMAT(created_at, '%Y-%m')
            ORDER BY month
        """)
        
        monthly_revenue = [{
            'month': row['month'],
            'revenue': float(row['revenue'])
        } for row in cur.fetchall()]
        
        return jsonify({
            'dailyOrders': daily_orders,
            'monthlyRevenue': monthly_revenue
        })
        
    except Exception as e:
        return jsonify({"message": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route("/admin/withdrawals/<int:withdrawal_id>", methods=["PUT"])
def update_withdrawal_status(withdrawal_id):
    try:
        data = request.get_json()
        if not data or 'status' not in data:
            return jsonify({"message": "Status is required"}), 400
            
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Update withdrawal status
        cur.execute("""
            UPDATE agent_withdrawals
            SET status = %s
            WHERE id = %s
        """, (data['status'], withdrawal_id))
        
        # If status is 'approved', update order_history status
        if data['status'] == 'approved':
            cur.execute("""
                UPDATE order_history oh
                JOIN withdrawn_orders wo ON oh.order_id = wo.order_id
                SET oh.is_paid_agent = 'approved'
                WHERE wo.withdrawal_id = %s
            """, (withdrawal_id,))
        
        conn.commit()
        return jsonify({"message": "Withdrawal status updated successfully"})
        
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"message": str(e)}), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=1245)
