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
        
        # WordPress configuration
        self.wordpress_url: Optional[str] = os.getenv('WORDPRESS_URL')
        self.wordpress_username: Optional[str] = os.getenv('WORDPRESS_USERNAME')
        self.wordpress_password: Optional[str] = os.getenv('WORDPRESS_PASSWORD')
        self.wordpress_domain: Optional[str] = os.getenv('WORDPRESS_DOMAIN')
        
        # Gemini configuration: supports multiple keys GEMINI_API_KEY, GEMINI_API_KEY_1, etc.
        self.gemini_keys = sorted([
            v for k, v in os.environ.items() 
            if k.startswith('GEMINI_API_KEY') and v
        ])
        
        # TMDB configuration
        # Provide default fallback values for local development to prevent crashes.
        # These will be used if the variables are not in the .env file.
        self.tmdb_api_key: Optional[str] = os.getenv(
            'TMDB_API_KEY', 'cb60717161e33e2972bd217aabaa27f4'
        )
        self.tmdb_read_token: Optional[str] = os.getenv(
            'TMDB_READ_TOKEN', 'eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJjYjYwNzE3MTYxZTMzZTI5NzJiZDIxN2FhYmFhMjdmNCIsIm5iZiI6MTY4OTI2MjQ1NC4zODYsInN1YiI6IjY0YjAxOTc2NmEzNDQ4MDE0ZDM1NDYyNCIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.vw6ILzP4aEOLFL-MbIMiwPVvZGOmxMwRLtjo2TJLzns'
        )
        
        # Validate required configuration
        self._validate_config()
        
        # Set primary Gemini key after validation
        self.gemini_api_key: str = self.gemini_keys[0]

        logger.info("Configuration loaded successfully")

    def get_gemini_api_keys(self):
        """Returns the list of all available Gemini API keys."""
        return self.gemini_keys

    def get_gemini_api_key(self):
        """Returns the primary Gemini API key."""
        return self.gemini_api_key
    
    def _validate_config(self):
        """Validate that all required configuration is present."""
        required_vars = [
            ('WORDPRESS_URL', self.wordpress_url),
            ('WORDPRESS_USERNAME', self.wordpress_username),
            ('WORDPRESS_PASSWORD', self.wordpress_password),
            ('WORDPRESS_DOMAIN', self.wordpress_domain),
            ('TMDB_API_KEY', self.tmdb_api_key),
            ('TMDB_READ_TOKEN', self.tmdb_read_token)
        ]
        
        missing_vars = []
        for var_name, var_value in required_vars:
            if not var_value:
                missing_vars.append(var_name)
        
        if not self.gemini_keys:
            missing_vars.append('GEMINI_API_KEY (or GEMINI_API_KEY_n)')

        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        # Validate URLs
        # The 'type: ignore' is safe here because we've just validated they are not None
        if not self.wordpress_url.startswith(('http://', 'https://')): # type: ignore
            raise ValueError("WORDPRESS_URL must start with http:// or https://")
        
        if not self.wordpress_domain.startswith(('http://', 'https://')): # type: ignore
            raise ValueError("WORDPRESS_DOMAIN must start with http:// or https://")
        
        logger.info("All required configuration validated")