#!/usr/bin/env python3
"""
Main orchestrator for WordPress SEO optimization automation.
Monitors posts by author João and optimizes them using Google Gemini 1.5 Pro.
"""

import logging
import time
import schedule
import sys
from datetime import datetime, timedelta
from typing import Set, Dict, Any
import json
import os

from config import Config
from wordpress_client import WordPressClient
from gemini_client import GeminiClient
from tmdb_client import TMDBClient
from process_lock import ProcessLock

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('seo_optimizer.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class SEOOptimizer:
    """Main class that orchestrates the SEO optimization process."""

    def __init__(self):
        """Initialize the SEO optimizer with clients and configuration."""
        self.config = Config()
        self.wp_client = WordPressClient(
            site_url=self.config.wordpress_url,
            username=self.config.wordpress_username,
            password=self.config.wordpress_password
        )
        
        # Initialize Gemini client with backup support
        gemini_api_keys = self.config.get_gemini_api_keys()
        logger.info(f"Initializing Gemini client with {len(gemini_api_keys)} API keys")
        self.gemini_client = GeminiClient(
            api_key=self.config.get_gemini_api_key(),
            backup_keys=gemini_api_keys
        )
        self.tmdb_client = TMDBClient(
            api_key=self.config.tmdb_api_key,
            read_token=self.config.tmdb_read_token
        )
        self.processed_posts: Set[int] = set()
        self.joao_author_id: int = 6  # João's known author ID

    def initialize(self) -> bool:
        """Initialize the optimizer by verifying connections."""
        try:
            # Test WordPress connection
            if not self.wp_client.test_connection():
                logger.error("Failed to connect to WordPress")
                return False

            # Test Gemini connection
            if not self.gemini_client.test_connection():
                logger.error("Failed to connect to Gemini API")
                return False

            # Test TMDB connection
            if not self.tmdb_client.test_connection():
                logger.error("Failed to connect to TMDB API")
                return False

            logger.info(f"Using João's author ID: {self.joao_author_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            return False

    def get_new_posts(self) -> list:
        """Get new posts by João that haven't been processed yet."""
        try:
            # Get posts from the last 24 hours by João
            since_date = (datetime.now() - timedelta(days=1)).isoformat()
            posts = self.wp_client.get_posts_by_author(
                author_id=self.joao_author_id,
                since=since_date
            )

            # Filter out already processed posts
            new_posts = [post for post in posts if post['id'] not in self.processed_posts]

            logger.info(f"Found {len(new_posts)} new posts by João")
            return new_posts

        except Exception as e:
            logger.error(f"Failed to get new posts: {e}")
            return []

    def optimize_post(self, post: Dict[str, Any]) -> bool:
        """Optimize a single post using Gemini AI."""
        try:
            post_id = post['id']
            logger.info(f"Optimizing post ID: {post_id} - '{post['title']['rendered']}'")

            # Prepare content for Gemini
            title = post['title']['rendered']
            excerpt = post['excerpt']['rendered']
            content = post['content']['rendered']
            tags = self.wp_client.get_post_tags(post_id)

            # Get post categories to determine content type
            categories = self.wp_client.get_post_categories(post_id)

            # Get media data from TMDB with category context
            logger.info(f"Searching for media content for post: {title}")
            media_data = self.tmdb_client.find_media_for_post(title, content, categories)

            # Get optimized content from Gemini with media
            optimized_content = self.gemini_client.optimize_content(
                title=title,
                excerpt=excerpt,
                content=content,
                tags=tags,
                domain=self.config.wordpress_domain,
                media_data=media_data
            )

            if not optimized_content:
                logger.error(f"Failed to get optimized content for post {post_id}")
                return False

            # Update the WordPress post
            success = self.wp_client.update_post(
                post_id=post_id,
                title=optimized_content['title'],
                excerpt=optimized_content['excerpt'],
                content=optimized_content['content']
            )

            if success:
                logger.info(f"Successfully optimized post {post_id}")
                self.processed_posts.add(post_id)
                return True
            else:
                logger.error(f"Failed to update post {post_id} in WordPress")
                return False

        except Exception as e:
            logger.error(f"Failed to optimize post {post.get('id', 'unknown')}: {e}")
            return False

    def run_optimization_cycle(self):
        """Run a single optimization cycle with quota management."""
        logger.info("Starting optimization cycle")

        try:
            # Check if quota is available before starting
            if not self.gemini_client._can_make_request():
                quota_data = self.gemini_client._load_quota_data()
                logger.warning(f"Skipping cycle - daily quota exceeded: {quota_data['requests']}/{self.gemini_client.max_daily_requests}")
                return

            new_posts = self.get_new_posts()

            if not new_posts:
                logger.info("No new posts to optimize")
                return

            # Limit posts processed per cycle to manage quota
            remaining_quota = self.gemini_client.max_daily_requests - self.gemini_client._load_quota_data()['requests']
            max_posts_per_cycle = min(2, remaining_quota)  # Don't exceed remaining quota
            posts_to_process = new_posts[:max_posts_per_cycle]

            logger.info(f"Processing {len(posts_to_process)} posts (remaining quota: {remaining_quota})")

            success_count = 0

            for i, post in enumerate(posts_to_process):
                logger.info(f"Processing post {i+1}/{len(posts_to_process)}")

                if self.optimize_post(post):
                    success_count += 1
                    # Add delay between posts to respect API rate limits
                    time.sleep(30)  # Increased delay to 30 seconds
                else:
                    logger.warning("Post optimization failed, stopping cycle")
                    break

            logger.info(f"Optimization cycle completed. {success_count}/{len(posts_to_process)} posts optimized successfully")

        except Exception as e:
            logger.error(f"Error during optimization cycle: {e}")

    def start_scheduler(self):
        """Start the scheduled optimization process."""
        logger.info("Starting SEO optimizer scheduler")

        # Schedule to run every 60 minutes to reduce API pressure
        schedule.every(60).minutes.do(self.run_optimization_cycle)

        # Run immediately on startup
        self.run_optimization_cycle()

        # Keep the scheduler running
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute


def main():
    """Main entry point."""
    logger.info("=== WordPress SEO Optimizer Started ===")

    # Use process lock to prevent multiple instances
    with ProcessLock() as acquired:
        if not acquired:
            logger.error("Another instance is already running. Exiting.")
            return 1

        try:
            optimizer = SEOOptimizer()

            if not optimizer.initialize():
                logger.error("Failed to initialize optimizer")
                return 1

            if len(sys.argv) > 1 and sys.argv[1] == '--once':
                # Run once for testing
                optimizer.run_optimization_cycle()
            else:
                # Run continuously with scheduler
                optimizer.start_scheduler()

        except KeyboardInterrupt:
            logger.info("SEO optimizer stopped by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}")
            return 1

    return 0


if __name__ == "__main__":
    exit(main())