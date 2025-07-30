"""
Configuration management using environment variables.
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class Config:
    """Configuration class that loads settings from environment variables."""
    
    def __init__(self):
        """Load configuration from environment variables."""
        # Load .env file if it exists
        load_dotenv()
        
        # WordPress configuration - temporarily store as Optional[str]
        _wordpress_url = os.getenv('WORDPRESS_URL')
        _wordpress_username = os.getenv('WORDPRESS_USERNAME')
        _wordpress_password = os.getenv('WORDPRESS_PASSWORD')
        _wordpress_domain = os.getenv('WORDPRESS_DOMAIN')
        
        # Gemini configuration
        _gemini_api_key = os.getenv('GEMINI_API_KEY', 'AIzaSyD7X2_8KPNZrnQnQ_643TjIJ2tpbkuRSms')
        
        # TMDB configuration
        _tmdb_api_key = os.getenv('TMDB_API_KEY', 'cb60717161e33e2972bd217aabaa27f4')
        _tmdb_read_token = os.getenv('TMDB_READ_TOKEN', 'eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJjYjYwNzE3MTYxZTMzZTI5NzJiZDIxN2FhYmFhMjdmNCIsIm5iZiI6MTY4OTI2MjQ1NC4zODYsInN1YiI6IjY0YjAxOTc2NmEzNDQ4MDE0ZDM1NDYyNCIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.vw6ILzP4aEOLFL-MbIMiwPVvZGOmxMwRLtjo2TJLzns')
        
        # Validate required configuration
        self._validate_config(_wordpress_url, _wordpress_username, _wordpress_password, _wordpress_domain, _gemini_api_key, _tmdb_api_key, _tmdb_read_token)
        
        # After validation, these properties are guaranteed to be non-None
        self.wordpress_url: str = _wordpress_url  # type: ignore
        self.wordpress_username: str = _wordpress_username  # type: ignore
        self.wordpress_password: str = _wordpress_password  # type: ignore
        self.wordpress_domain: str = _wordpress_domain  # type: ignore
        self.gemini_api_key: str = _gemini_api_key  # type: ignore
        self.tmdb_api_key: str = _tmdb_api_key  # type: ignore
        self.tmdb_read_token: str = _tmdb_read_token  # type: ignore
        
        logger.info("Configuration loaded successfully")
    
    def _validate_config(self, wordpress_url: Optional[str], wordpress_username: Optional[str], 
                         wordpress_password: Optional[str], wordpress_domain: Optional[str], 
                         gemini_api_key: Optional[str], tmdb_api_key: Optional[str], 
                         tmdb_read_token: Optional[str]):
        """Validate that all required configuration is present."""
        required_vars = [
            ('WORDPRESS_URL', wordpress_url),
            ('WORDPRESS_USERNAME', wordpress_username),
            ('WORDPRESS_PASSWORD', wordpress_password),
            ('WORDPRESS_DOMAIN', wordpress_domain),
            ('GEMINI_API_KEY', gemini_api_key),
            ('TMDB_API_KEY', tmdb_api_key),
            ('TMDB_READ_TOKEN', tmdb_read_token)
        ]
        
        missing_vars = []
        for var_name, var_value in required_vars:
            if not var_value:
                missing_vars.append(var_name)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        # Validate URLs
        if not wordpress_url or not wordpress_url.startswith(('http://', 'https://')):
            raise ValueError("WORDPRESS_URL must start with http:// or https://")
        
        if not wordpress_domain or not wordpress_domain.startswith(('http://', 'https://')):
            raise ValueError("WORDPRESS_DOMAIN must start with http:// or https://")
        
        logger.info("All required configuration validated")
