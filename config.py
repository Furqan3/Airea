"""Configuration settings for AIREA Real Estate Chatbot."""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration."""
    
    # API Configuration
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable is required")
    
    # Database Configuration
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'real_estate_clients.db')
    
    # Email Configuration
    EMAIL_CONFIG = {
        'mailjet_api_key': os.getenv('MAILJET_API_KEY'),
        'mailjet_secret_key': os.getenv('MAILJET_SECRET_KEY'),
        'sender_email': os.getenv('SENDER_EMAIL', 'info@askairea.com'),
        'sender_name': os.getenv('SENDER_NAME', 'AIREA Real Estate'),
        'agent_email': os.getenv('AGENT_EMAIL', 'agent@askairea.com')
    }
    
    # API Configuration
    API_TITLE = "AIREA Real Estate Chatbot API"
    API_DESCRIPTION = "AI-powered real estate assistant with lead management"
    API_VERSION = "1.0.0"
    
    # CORS Configuration
    CORS_ORIGINS = ["*"]  # Configure appropriately for production
    
    # Frontend Configuration
    FRONTEND_PATH = "frontend/out"
    
    @classmethod
    def validate_email_config(cls) -> bool:
        """Validate email configuration."""
        return bool(cls.EMAIL_CONFIG['mailjet_api_key'] and cls.EMAIL_CONFIG['mailjet_secret_key'])