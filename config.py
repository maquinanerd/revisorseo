"""
Configuration management using environment variables.
"""

import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class Config:
    """Configuration class that loads settings from environment variables."""
    
    def __init__(self):
        """Load configuration from environment variables."""
        # Load .env file if it exists
        load_dotenv()
        
        # WordPress configuration
        self.wordpress_url = os.getenv('WORDPRESS_URL')
        self.wordpress_username = os.getenv('WORDPRESS_USERNAME')
        self.wordpress_password = os.getenv('WORDPRESS_PASSWORD')
        self.wordpress_domain = os.getenv('WORDPRESS_DOMAIN')
        
        # Gemini configuration
        self.gemini_api_key = os.getenv('GEMINI_API_KEY', 'AIzaSyD7X2_8KPNZrnQnQ_643TjIJ2tpbkuRSms')
        
        # Validate required configuration
        self._validate_config()
        
        logger.info("Configuration loaded successfully")
    
    def _validate_config(self):
        """Validate that all required configuration is present."""
        required_vars = [
            ('WORDPRESS_URL', self.wordpress_url),
            ('WORDPRESS_USERNAME', self.wordpress_username),
            ('WORDPRESS_PASSWORD', self.wordpress_password),
            ('WORDPRESS_DOMAIN', self.wordpress_domain),
            ('GEMINI_API_KEY', self.gemini_api_key)
        ]
        
        missing_vars = []
        for var_name, var_value in required_vars:
            if not var_value:
                missing_vars.append(var_name)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        # Validate URLs
        if not self.wordpress_url or not self.wordpress_url.startswith(('http://', 'https://')):
            raise ValueError("WORDPRESS_URL must start with http:// or https://")
        
        if not self.wordpress_domain or not self.wordpress_domain.startswith(('http://', 'https://')):
            raise ValueError("WORDPRESS_DOMAIN must start with http:// or https://")
        
        logger.info("All required configuration validated")
