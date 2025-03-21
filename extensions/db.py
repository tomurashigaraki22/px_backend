import pymysql
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_connection():
    """
    Create and return a connection to the database using PyMySQL
    """
    connection = pymysql.connect(
        host=os.getenv('DB_HOST'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME'),
        port=int(os.getenv('DB_PORT')),
    )
    return connection

def execute_query(query, params=None):
    """
    Execute a query and return the results
    """
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, params or ())
            if query.strip().upper().startswith('SELECT'):
                return cursor.fetchall()
            connection.commit()
            return cursor.rowcount
    finally:
        connection.close()

def execute_many(query, params_list):
    """
    Execute a query with multiple parameter sets
    """
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.executemany(query, params_list)
            connection.commit()
            return cursor.rowcount
    finally:
        connection.close()