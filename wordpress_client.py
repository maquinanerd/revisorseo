# Increased timeout value for WordPress API requests.
"""
WordPress REST API client for managing posts and authentication.
"""

import requests
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin
import base64

logger = logging.getLogger(__name__)


class WordPressClient:
    """Client for interacting with WordPress REST API."""

    def __init__(self, site_url: str, username: str, password: str):
        """
        Initialize WordPress client with authentication.

        Args:
            site_url: WordPress site URL
            username: WordPress username
            password: WordPress application password
        """
        self.site_url = site_url.rstrip('/')
        self.api_base = urljoin(self.site_url, '/wp-json/wp/v2/')
        self.session = requests.Session()

        # Set up authentication (Basic Auth with application password)
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        self.session.headers.update({
            'Authorization': f'Basic {credentials}',
            'Content-Type': 'application/json',
            'User-Agent': 'WordPress-SEO-Optimizer/1.0'
        })

        logger.info(f"WordPress client initialized for {site_url}")

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Make a request to the WordPress API with error handling."""
        url = urljoin(self.api_base, endpoint)

        try:
            response = self.session.request(method, url, timeout=60, **kwargs)
            response.raise_for_status()

            if response.content:
                return response.json()
            return {}

        except requests.exceptions.RequestException as e:
            logger.error(f"WordPress API request failed: {method} {url} - {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response body: {e.response.text}")
            return None

    def get_authors(self) -> List[Dict[str, Any]]:
        """Get all authors from WordPress."""
        authors = self._make_request('GET', 'users', params={'per_page': 100})
        if isinstance(authors, list):
            return authors
        return []

    def get_posts_by_author(self, author_id: int, since: Optional[str] = None, per_page: int = 10) -> List[Dict[str, Any]]:
        """
        Get posts by a specific author.

        Args:
            author_id: WordPress author ID
            since: ISO datetime string to filter posts after this date
            per_page: Number of posts per page

        Returns:
            List of post dictionaries
        """
        params = {
            'author': author_id,
            'status': 'publish',
            'per_page': per_page,
            '_embed': 'wp:term'  # Include tags and categories
        }

        if since:
            params['after'] = since

        posts = self._make_request('GET', 'posts', params=params)
        if isinstance(posts, list):
            return posts
        return []

    def get_post_tags(self, post_id: int) -> List[str]:
        """Get tags for a specific post."""
        try:
            post = self._make_request('GET', f'posts/{post_id}', params={'_embed': 'wp:term'})
            if not post:
                return []

            tags = []
            if '_embedded' in post and 'wp:term' in post['_embedded']:
                for term_group in post['_embedded']['wp:term']:
                    for term in term_group:
                        if term.get('taxonomy') == 'post_tag':
                            tags.append(term.get('slug', ''))

            return [tag for tag in tags if tag]

        except Exception as e:
            logger.error(f"Failed to get tags for post {post_id}: {e}")
            return []

    def update_post(self, post_id: int, title: str, excerpt: str, content: str) -> bool:
        """
        Update a WordPress post with new content.

        Args:
            post_id: WordPress post ID
            title: New post title
            excerpt: New post excerpt
            content: New post content (HTML)

        Returns:
            True if successful, False otherwise
        """
        data = {
            'title': title,
            'excerpt': excerpt,
            'content': content,
            'status': 'publish'  # Ensure post remains published
        }

        result = self._make_request('POST', f'posts/{post_id}', json=data)

        if result:
            logger.info(f"Successfully updated post {post_id}")
            return True
        else:
            logger.error(f"Failed to update post {post_id}")
            return False

    def get_post(self, post_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific post by ID."""
        return self._make_request('GET', f'posts/{post_id}')

    def test_connection(self) -> bool:
        """Test the WordPress API connection."""
        try:
            result = self._make_request('GET', '')
            if result and 'namespace' in result and result['namespace'] == 'wp/v2':
                logger.info(f"Successfully connected to WordPress API at {self.site_url}")
                return True
            else:
                logger.error("Failed to connect to WordPress API - invalid response")
                return False
        except Exception as e:
            logger.error(f"WordPress connection test failed: {e}")
            return False