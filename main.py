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
from typing import Set, Dict, Any, List, Optional
import json
import os

from config import Config
from wordpress_client import WordPressClient
from gemini_client import GeminiClient
from tmdb_client import TMDBClient
from dashboard import SEODashboard # Import the dashboard class
from process_lock import ProcessLock
import sqlite3

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

    def __init__(self, dry_run: bool = False):
        """Initialize the SEO optimizer with clients and configuration."""
        self.dry_run = dry_run
        self.config = Config()
        self.wp_client = WordPressClient(
            site_url=self.config.wordpress_url,
            username=self.config.wordpress_username,
            password=self.config.wordpress_password,
            timeout=self.config.wordpress_timeout
        )
        
        # Initialize Gemini client with backup support
        gemini_api_keys = self.config.get_gemini_api_keys()
        logger.info(f"Initializing Gemini client with {len(gemini_api_keys)} API keys")
        self.gemini_client = GeminiClient(api_keys=gemini_api_keys)
        self.tmdb_client = TMDBClient(
            api_key=self.config.tmdb_api_key,
            read_token=self.config.tmdb_read_token
        )
        self.dashboard = SEODashboard() # Initialize dashboard for logging
        self.processed_posts: Set[int] = set()
        self.joao_author_id: int = 6  # João's known author ID
        # Use environment variable for DB path for Render compatibility
        self.db_path = os.getenv('DB_PATH', 'seo_dashboard.db')


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

    def _get_successfully_optimized_post_ids(self) -> Set[int]:
        """Get a set of post IDs that have already been successfully optimized from the database."""
        if not os.path.exists(self.db_path):
            logger.warning(f"Dashboard database '{self.db_path}' not found. Cannot check for previously optimized posts.")
            return set()

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT post_id FROM optimization_history WHERE status = 'success'")
                optimized_ids = {row[0] for row in cursor.fetchall()}
                logger.info(f"Found {len(optimized_ids)} successfully optimized posts in the database.")
                return optimized_ids
        except Exception as e:
            logger.error(f"Failed to query successfully optimized posts from database: {e}")
            return set()

    def get_new_posts(self) -> List[Dict[str, Any]]:
        """Get new posts by João that haven't been processed yet."""
        try:
            # Get posts from the last 24 hours by João
            since_date = (datetime.now() - timedelta(days=1)).isoformat()
            posts = self.wp_client.get_posts_by_author(
                author_id=self.joao_author_id,
                since=since_date,
                per_page=20 # Fetch more to ensure we find some new ones
            )

            # Get IDs of posts already optimized successfully from the database
            successfully_optimized_ids = self._get_successfully_optimized_post_ids()

            # Filter out already processed posts (in this session or from DB)
            new_posts = [
                post for post in posts
                if post['id'] not in self.processed_posts and post['id'] not in successfully_optimized_ids
            ]

            logger.info(f"Found {len(posts)} recent posts, {len(new_posts)} are new and need optimization.")
            return new_posts

        except Exception as e:
            logger.error(f"Failed to get new posts: {e}")
            return []

    def _perform_optimization_steps(self, post: Dict[str, Any]) -> Optional[Dict[str, str]]:
        """
        Performs the actual steps of fetching data and calling APIs for optimization.
        Returns the optimized content dictionary or None on failure.
        """
        post_id = post['id']
        title = post['title']['rendered']
        excerpt = post['excerpt']['rendered']
        content = post['content']['rendered']

        # 1. Fetch WordPress metadata
        tags = self.wp_client.get_post_tags(post_id)
        categories = self.wp_client.get_post_categories(post_id)

        # 2. Fetch media data from TMDB
        logger.info(f"Searching for media content for post: {title}")
        media_data = self.tmdb_client.find_media_for_post(title, content, categories)

        # 3. Get optimized content from Gemini
        optimized_content = self.gemini_client.optimize_content(
            title=title,
            excerpt=excerpt,
            content=content,
            tags=tags,
            domain=self.config.wordpress_domain,
            media_data=media_data
        )
        return optimized_content

    def optimize_post(self, post: Dict[str, Any]) -> bool:
        """
        Orchestrates the optimization of a single post, handling logging,
        state, and updates.
        """
        post_id = post['id']
        title = post['title']['rendered']
        logger.info(f"Optimizing post ID: {post_id} - '{title}'")

        # Mark post as 'processing' in the dashboard database
        self.dashboard.mark_post_processing(post_id, title)

        try:
            optimized_content = self._perform_optimization_steps(post)

            if not optimized_content:
                error_msg = f"Failed to get optimized content from Gemini for post {post_id}"
                logger.error(error_msg)
                self.dashboard.log_optimization(post_id, title, 'failed', error_message=error_msg)
                return False

            if self.dry_run:
                logger.info(f"--- [DRY RUN] Post {post_id} ---")
                logger.info(f"Original Title: {title}")
                logger.info(f"Optimized Title: {optimized_content['title']}")
                logger.info(f"Optimized Excerpt: {optimized_content['excerpt']}")
                logger.info(f"Content length: {len(optimized_content['content'])} chars")
                logger.info("Post would be updated, but DRY RUN is active.")
                self.dashboard.log_optimization(post_id, title, 'success', recommendations="Dry run, no changes applied.")
                self.processed_posts.add(post_id)
                # Return true to allow the cycle to continue processing other posts in dry run mode
                return True

            # Update the WordPress post
            success = self.wp_client.update_post(
                post_id=post_id,
                title=optimized_content['title'],
                excerpt=optimized_content['excerpt'],
                content=optimized_content['content']
            )

            if success:
                logger.info(f"Successfully optimized post {post_id}")
                # Log success to dashboard DB, using a default score like the dashboard does
                self.dashboard.log_optimization(post_id, title, 'success', seo_score=85)
                self.processed_posts.add(post_id)
                return True
            else:
                error_msg = f"Failed to update post {post_id} in WordPress"
                logger.error(error_msg)
                self.dashboard.log_optimization(post_id, title, 'failed', error_message=error_msg)
                return False

        except Exception as e:
            error_msg = f"Failed to optimize post {post_id}: {e}"
            logger.error(error_msg)
            self.dashboard.log_optimization(post_id, title, 'failed', error_message=str(e))
            return False

    def run_optimization_cycle(self):
        """Run a single optimization cycle with quota management."""
        logger.info("Starting optimization cycle")

        try:
            new_posts = self.get_new_posts()

            if not new_posts:
                logger.info("No new posts to optimize")
                return

            # Limit to 2 posts per cycle to manage API usage and avoid long runs
            posts_to_process = new_posts[:2]

            logger.info(f"Processing up to {len(posts_to_process)} posts in this cycle.")

            success_count = 0

            for i, post in enumerate(posts_to_process):
                logger.info(f"Processing post {i+1}/{len(posts_to_process)}")

                if self.optimize_post(post):
                    success_count += 1
                else:
                    logger.warning(f"Optimization failed for post ID {post.get('id', 'unknown')}. Continuing to the next post.")

                # Add a delay between processing posts to respect API rate limits, regardless of the outcome.
                if i < len(posts_to_process) - 1:
                    time.sleep(30)
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
            is_dry_run = '--dry-run' in sys.argv
            optimizer = SEOOptimizer(dry_run=is_dry_run)

            if is_dry_run:
                logger.info("🚀 Running in DRY-RUN mode. No posts will be updated on WordPress. 🚀")

            if not optimizer.initialize():
                logger.error("Failed to initialize optimizer. Exiting.")
                return 1

            if '--once' in sys.argv:
                # Run once for testing or dry-run
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