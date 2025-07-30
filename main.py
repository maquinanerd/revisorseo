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
        self.gemini_client = GeminiClient(api_key=self.config.gemini_api_key)
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
            
            # Get optimized content from Gemini
            optimized_content = self.gemini_client.optimize_content(
                title=title,
                excerpt=excerpt,
                content=content,
                tags=tags,
                domain=self.config.wordpress_domain
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
        """Run a single optimization cycle."""
        logger.info("Starting optimization cycle")
        
        try:
            new_posts = self.get_new_posts()
            
            if not new_posts:
                logger.info("No new posts to optimize")
                return
            
            success_count = 0
            for post in new_posts:
                if self.optimize_post(post):
                    success_count += 1
                    # Add delay between posts to respect API rate limits
                    time.sleep(2)
            
            logger.info(f"Optimization cycle completed. {success_count}/{len(new_posts)} posts optimized successfully")
            
        except Exception as e:
            logger.error(f"Error during optimization cycle: {e}")
    
    def start_scheduler(self):
        """Start the scheduled optimization process."""
        logger.info("Starting SEO optimizer scheduler")
        
        # Schedule to run every 30 minutes
        schedule.every(30).minutes.do(self.run_optimization_cycle)
        
        # Run immediately on startup
        self.run_optimization_cycle()
        
        # Keep the scheduler running
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute


def main():
    """Main entry point."""
    logger.info("=== WordPress SEO Optimizer Started ===")
    
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
