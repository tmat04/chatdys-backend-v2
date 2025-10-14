"""
ChatDys Backend - Main Application
Clean, modular Flask application with proper separation of concerns
"""

from flask import Flask
from flask_cors import CORS
from config.settings import Config
from database.connection import init_database
from api.auth_routes import auth_bp
from api.chat_routes import chat_bp
from api.user_routes import user_bp
from api.payment_routes import payment_bp
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(Config)
    
    # Enable CORS
    CORS(app)
    
    # Initialize database
    init_database(app)
    
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(user_bp, url_prefix='/api/user')
    app.register_blueprint(payment_bp, url_prefix='/api/payments')
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {
            'status': 'healthy',
            'version': '2.0.0',
            'service': 'chatdys-backend'
        }
    
    logger.info("ChatDys Backend initialized successfully")
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(Config.PORT)
    app.run(host='0.0.0.0', port=port, debug=False)
