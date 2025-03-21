from flask import Flask
from flask_cors import CORS
from flask_mail import Mail
import pymysql
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, template_folder='../templates')
CORS(app)

# Configure mail settings
app.config.update(
    MAIL_SERVER='kepler11b.titanwebserver.com',
    MAIL_PORT=465,
    MAIL_USERNAME='pxsm@pxs.name.ng',
    MAIL_PASSWORD='Pityboy@22',
    MAIL_USE_SSL=True,
    MAIL_USE_TLS=False,
    MAIL_DEFAULT_SENDER='pxsm@pxs.name.ng'
)

# Initialize Flask-Mail
mail = Mail(app)

def db_connection():
    """Create and return a database connection"""
    try:
        connection = pymysql.connect(
            host=os.getenv('DB_HOST'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME'),
            port=int(os.getenv('DB_PORT')),
            cursorclass=pymysql.cursors.DictCursor,
            ssl={'ssl': True},
            connect_timeout=10
        )
        return connection
    except pymysql.Error as e:
        print(f"Database connection error: {e}")
        raise Exception(f"Failed to connect to database: {str(e)}")

def setup_extensions():
    """Setup all extensions for the Flask app"""
    # Configure request size limits for payload
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max payload
    
    # Configure Flask-Mail with dummy settings
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.example.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', 'user@example.com')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', 'password')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER', 'noreply@example.com')
    
    # Initialize mail
    mail.init_app(app)
    
    # Configure other app settings
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
    app.config['JSON_SORT_KEYS'] = False