def create_users_table(connection):
    with connection.cursor() as cursor:
        sql = """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            email VARCHAR(100) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL,
            balance DECIMAL(10, 2) DEFAULT 0.00,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_email (email),
            INDEX idx_username (username)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        cursor.execute(sql)
        connection.commit()

def alter_agent_withdrawals_table(connection):
    try:
        with connection.cursor() as cursor:
            if not column_exists(cursor, "agent_withdrawals", "bank_name"):
                print("Adding bank_name column...")
                cursor.execute("ALTER TABLE agent_withdrawals ADD COLUMN bank_name VARCHAR(255) NOT NULL;")
            if not column_exists(cursor, "agent_withdrawals", "account_number"):
                print("Adding account_number column...")
                cursor.execute("ALTER TABLE agent_withdrawals ADD COLUMN account_number VARCHAR(255) NOT NULL;")
            connection.commit()
            print("Agent withdrawals table altered successfully")
    except Exception as e:
        print(f"Error altering agent_withdrawals table: {str(e)}")
        connection.rollback()


def column_exists(cursor, table_name, column_name):
    cursor.execute("""
        SELECT COUNT(*) as count FROM information_schema.COLUMNS
        WHERE TABLE_NAME=%s AND COLUMN_NAME=%s
    """, (table_name, column_name))
    result = cursor.fetchone()
    if result and 'count' in result:
        return result['count'] > 0
    return False

def alter_users_table(connection):
    try:
        with connection.cursor() as cursor:
            if not column_exists(cursor, "users", "agent_id"):
                print("Adding agent_id column...")
                cursor.execute("ALTER TABLE users ADD COLUMN agent_id VARCHAR(255) DEFAULT NULL;")
            if not column_exists(cursor, "users", "is_agent"):
                print("Adding is_agent column...")
                cursor.execute("ALTER TABLE users ADD COLUMN is_agent BOOLEAN DEFAULT FALSE;")
            if not column_exists(cursor, "users", "agent_password"):
                print("Adding agent_password column...")
                cursor.execute("ALTER TABLE users ADD COLUMN agent_password VARCHAR(255) DEFAULT NULL;")
            connection.commit()
            print("Users table altered successfully")

    except Exception as e:
        print(f"Error altering users table: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error details: {repr(e)}")
        connection.rollback()


def create_transactions_table(connection):
    with connection.cursor() as cursor:
        sql = """
        CREATE TABLE IF NOT EXISTS transactions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            type ENUM('credit', 'debit') NOT NULL,
            amount DECIMAL(10, 2) NOT NULL,
            previous_balance DECIMAL(10, 2) NOT NULL,
            new_balance DECIMAL(10, 2) NOT NULL,
            status ENUM('pending', 'completed', 'failed') DEFAULT 'pending',
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            INDEX idx_user_id (user_id),
            INDEX idx_type (type),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        cursor.execute(sql)
        connection.commit()

def create_order_history_table(connection):
    with connection.cursor() as cursor:
        sql = """
        CREATE TABLE IF NOT EXISTS order_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            order_id VARCHAR(100) NOT NULL UNIQUE,
            service_name VARCHAR(255) NOT NULL,
            link VARCHAR(255) NOT NULL,
            amount DECIMAL(10, 2) NOT NULL,
            status ENUM('pending', 'completing', 'completed', 'cancelled') DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            INDEX idx_user_id (user_id),
            INDEX idx_order_id (order_id),
            INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        cursor.execute(sql)
        connection.commit()

def create_agent_info_table(connection):
    with connection.cursor() as cursor:
        print("Creating agent_info table...")
        sql = """
        CREATE TABLE IF NOT EXISTS agent_info (
            id INT AUTO_INCREMENT PRIMARY KEY,
            agent_id VARCHAR(255) NOT NULL,
            agent_user_id INT NOT NULL,
            subscription_type ENUM('basic', 'premium') NOT NULL,
            commission_rate DECIMAL(4, 2) NOT NULL,
            subscription_amount DECIMAL(10, 2) NOT NULL,
            is_paid BOOLEAN DEFAULT FALSE,
            subscription_start_date TIMESTAMP NULL,
            subscription_end_date TIMESTAMP NULL,
            total_earnings DECIMAL(10, 2) DEFAULT 0.00,
            pending_earnings DECIMAL(10, 2) DEFAULT 0.00,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            paid_at TIMESTAMP NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (agent_user_id) REFERENCES users(id) ON DELETE CASCADE,
            INDEX idx_agent_id (agent_id),
            INDEX idx_agent_user_id (agent_user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        cursor.execute(sql)
        print("Agent_info table created successfully")
        connection.commit()

def alter_order_history_table(connection):
    with connection.cursor() as cursor:
        if not column_exists(cursor, "order_history", "agent_id"):
            print("Adding agent_id column...")
            cursor.execute("ALTER TABLE order_history ADD COLUMN agent_id VARCHAR(255) DEFAULT NULL;")
        if not column_exists(cursor, "order_history", "commission"):
            print("Adding commission column...")
            cursor.execute("ALTER TABLE order_history ADD COLUMN commission DECIMAL(10, 2) DEFAULT 0.00;")
        if not column_exists(cursor, "order_history", "is_paid_agent"):
            print("Adding is_paid_agent column...")
            cursor.execute("""
                ALTER TABLE order_history 
                ADD COLUMN is_paid_agent ENUM('pending', 'processing', 'approved', 'failed') 
                DEFAULT 'pending'
            """)
        connection.commit()
        print("Order_history table altered successfully")

def create_agent_withdrawals_table(connection):
    with connection.cursor() as cursor:
        sql = """
        CREATE TABLE IF NOT EXISTS agent_withdrawals (
            id INT AUTO_INCREMENT PRIMARY KEY,
            agent_id VARCHAR(255) NOT NULL,
            amount DECIMAL(10, 2) NOT NULL,
            order_ids TEXT NOT NULL,
            transaction_reference VARCHAR(255) NOT NULL UNIQUE,
            email VARCHAR(255) GENERATED ALWAYS AS (CONCAT(agent_id, '@gmail.com')) STORED,
            status ENUM('pending', 'approved', 'processing') DEFAULT 'pending',
            bank_name VARCHAR(255) NOT NULL,
            account_number VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_agent_id (agent_id),
            INDEX idx_status (status),
            INDEX idx_transaction_reference (transaction_reference)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        cursor.execute(sql)
        connection.commit()

def create_withdrawn_orders_table(connection):
    with connection.cursor() as cursor:
        sql = """
        CREATE TABLE IF NOT EXISTS withdrawn_orders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            withdrawal_id INT NOT NULL,
            order_id VARCHAR(100) NOT NULL,
            agent_id VARCHAR(255) NOT NULL,
            amount DECIMAL(10, 2) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (withdrawal_id) REFERENCES agent_withdrawals(id) ON DELETE CASCADE,
            INDEX idx_order_id (order_id),
            INDEX idx_agent_id (agent_id),
            UNIQUE KEY unique_order_withdrawal (order_id, withdrawal_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
        cursor.execute(sql)
        connection.commit()



# Update init_database function
def init_database(connection):
    create_users_table(connection)
    create_transactions_table(connection)
    alter_users_table(connection)
    create_order_history_table(connection)
    create_agent_info_table(connection)
    alter_order_history_table(connection)
    create_agent_withdrawals_table(connection)
    create_withdrawn_orders_table(connection)
    alter_agent_withdrawals_table(connection)  # Add this line