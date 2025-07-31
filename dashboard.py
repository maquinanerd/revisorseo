#!/usr/bin/env python3
"""
Visual SEO Recommendation Dashboard for WordPress SEO Optimizer.
Provides a web interface to monitor and manage SEO optimization status.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from flask import Flask, render_template, jsonify, request, g
import sqlite3
import os

from config import Config
from wordpress_client import WordPressClient
from gemini_client import GeminiClient
from tmdb_client import TMDBClient

logger = logging.getLogger(__name__)

class SEODashboard:
    """SEO Recommendation Dashboard with visual interface."""

    def __init__(self):
        """Initialize the dashboard with database and clients."""
        self.config = Config()
        self.wp_client = WordPressClient(
            site_url=self.config.wordpress_url,
            username=self.config.wordpress_username,
            password=self.config.wordpress_password,
            timeout=self.config.wordpress_timeout
        )
        self.gemini_client = GeminiClient(api_keys=self.config.get_gemini_api_keys())
        self.tmdb_client = TMDBClient(
            api_key=self.config.tmdb_api_key,
            read_token=self.config.tmdb_read_token
        )
        # Use environment variable for DB path for Render compatibility,
        # with a local fallback.
        self.db_path = os.getenv('DB_PATH', 'seo_dashboard.db')
        self.init_database()
        self.update_daily_metrics() # Ensure metrics are updated on startup
        
        # Simple in-memory cache
        self.cache: Dict[str, Any] = {}
        self.cache_ttl = timedelta(seconds=60)  # Cache for 60 seconds

    def init_database(self):
        """Initialize SQLite database for tracking optimization history."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS optimization_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL,
                    optimization_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    error_message TEXT,
                    seo_score INTEGER,
                    recommendations TEXT
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS seo_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    total_posts INTEGER DEFAULT 0,
                    optimized_posts INTEGER DEFAULT 0,
                    failed_posts INTEGER DEFAULT 0,
                    avg_seo_score REAL DEFAULT 0
                )
            ''')
            conn.commit()

    def _invalidate_cache(self, key: str = 'dashboard_data'):
        """Invalidate a specific key in the cache."""
        if self.cache.pop(key, None):
            logger.info(f"Cache for '{key}' invalidated.")

    def log_optimization(self, post_id: int, title: str, status: str,
                        error_message: Optional[str] = None, seo_score: Optional[int] = None,
                        recommendations: Optional[str] = None):
        """Log optimization attempt to database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO optimization_history
                (post_id, title, status, error_message, seo_score, recommendations)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (post_id, title, status, error_message, seo_score, recommendations))
            conn.commit()
            self._invalidate_cache()  # Invalidate cache on data change

    def update_daily_metrics(self):
        """Update daily SEO metrics."""
        today = datetime.now().strftime('%Y-%m-%d')

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Get today's statistics
            cursor.execute('''
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as optimized,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    AVG(CASE WHEN seo_score IS NOT NULL THEN seo_score ELSE 0 END) as avg_score
                FROM optimization_history
                WHERE DATE(optimization_date) = ?
            ''', (today,))

            result = cursor.fetchone()
            total, optimized, failed, avg_score = result

            # Insert or update today's metrics
            cursor.execute('''
                INSERT OR REPLACE INTO seo_metrics
                (date, total_posts, optimized_posts, failed_posts, avg_seo_score)
                VALUES (?, ?, ?, ?, ?)
            ''', (today, total or 0, optimized or 0, failed or 0, avg_score or 0))
            conn.commit()
            self._invalidate_cache()  # Invalidate cache on data change

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data with caching."""
        # Check cache first
        now = datetime.now()
        cached_item = self.cache.get('dashboard_data')
        if cached_item and (now - cached_item['timestamp'] < self.cache_ttl):
            logger.info("Returning dashboard data from cache.")
            return cached_item['data']

        logger.info("Fetching fresh dashboard data from database.")


        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Recent optimizations (last 24 hours)
            cursor.execute('''
                SELECT post_id, title, status, optimization_date, error_message, seo_score
                FROM optimization_history
                WHERE optimization_date >= datetime('now', '-1 day')
                ORDER BY optimization_date DESC
                LIMIT 20
            ''')
            recent_optimizations = [
                {
                    'post_id': row[0],
                    'title': row[1],
                    'status': row[2],
                    'date': row[3],
                    'error': row[4],
                    'seo_score': row[5]
                }
                for row in cursor.fetchall()
            ]

            # Weekly metrics
            cursor.execute('''
                SELECT date, total_posts, optimized_posts, failed_posts, avg_seo_score
                FROM seo_metrics
                WHERE date >= date('now', '-7 days')
                ORDER BY date DESC
            ''')
            weekly_metrics = [
                {
                    'date': row[0],
                    'total': row[1],
                    'optimized': row[2],
                    'failed': row[3],
                    'avg_score': row[4]
                }
                for row in cursor.fetchall()
            ]

            # Summary statistics
            cursor.execute('''
                SELECT
                    COUNT(*) as total_all_time,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as total_optimized,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as total_failed
                FROM optimization_history
            ''')
            summary = cursor.fetchone()

            data = {
                'recent_optimizations': recent_optimizations,
                'weekly_metrics': weekly_metrics,
                'summary': {
                    'total_posts': summary[0] or 0,
                    'optimized_posts': summary[1] or 0,
                    'failed_posts': summary[2] or 0,
                    'success_rate': (summary[1] / summary[0] * 100) if summary[0] > 0 else 0
                }
            }

            # Store in cache
            self.cache['dashboard_data'] = {
                'timestamp': now,
                'data': data
            }

            return data

    def get_pending_posts(self) -> List[Dict[str, Any]]:
        """Get posts that need optimization - limited to 5 posts in batches."""
        try:
            # Get recent posts by João (last 30 days to have enough posts)
            since_date = (datetime.now() - timedelta(days=30)).isoformat()
            posts = self.wp_client.get_posts_by_author(
                author_id=6,  # João's author ID
                since=since_date,
                per_page=100  # Get more posts to work with
            )

            # Check which posts haven't been optimized and which are in progress
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT DISTINCT post_id FROM optimization_history 
                    WHERE status = 'success'
                ''')
                optimized_post_ids = {row[0] for row in cursor.fetchall()}

                # Get posts currently being processed
                cursor.execute('''
                    SELECT DISTINCT post_id FROM optimization_history 
                    WHERE status = 'processing' AND 
                    datetime(optimization_date) > datetime('now', '-1 hour')
                ''')
                processing_post_ids = {row[0] for row in cursor.fetchall()}

            # Filter unprocessed posts
            unprocessed_posts = []
            for post in posts:
                if (post['id'] not in optimized_post_ids and 
                    post['id'] not in processing_post_ids):
                    unprocessed_posts.append({
                        'id': post['id'],
                        'title': post['title']['rendered'],
                        'date': post['date'],
                        'status': post['status'],
                        'link': post['link']
                    })

            # Return only first 5 posts (batch processing)
            return unprocessed_posts[:5]

        except Exception as e:
            logger.error(f"Failed to get pending posts: {e}")
            return []

    def mark_post_processing(self, post_id: int, title: str):
        """Mark a post as currently being processed."""
        self.log_optimization(post_id, title, 'processing')

    def clear_old_processing_status(self):
        """Clear processing status for posts older than 1 hour."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM optimization_history 
                    WHERE status = 'processing' AND 
                    optimization_date < datetime('now', '-1 hour')
                ''')
                deleted_rows = cursor.rowcount
                conn.commit()
                if deleted_rows > 0:
                    logger.info(f"Cleared {deleted_rows} old 'processing' statuses.")
                    self._invalidate_cache()  # Invalidate cache if data changed
        except Exception as e:
            logger.error(f"Failed to clear old processing status: {e}")

# Flask Web Application
app = Flask(__name__)
app.secret_key = os.urandom(24)

dashboard = SEODashboard() # This now runs init_database and update_daily_metrics

@app.before_request
def before_request_hook():
    """Clear stale 'processing' statuses before handling a request."""
    # Use the 'g' object to ensure this runs only once per request
    if not hasattr(g, 'processing_cleared'):
        dashboard.clear_old_processing_status()
        g.processing_cleared = True

@app.route('/')
def index():
    """Main dashboard page."""
    data = dashboard.get_dashboard_data()
    pending_posts = dashboard.get_pending_posts()
    return render_template('dashboard.html', 
                         dashboard_data=data, 
                         pending_posts=pending_posts)

@app.route('/api/dashboard-data')
def get_dashboard_data():
    """Get dashboard data including summary and posts."""
    try:
        # The before_request_hook has already cleared old statuses
        data = dashboard.get_dashboard_data()
        return jsonify(data)
    except Exception as e:
        logger.error(f"Failed to get dashboard data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/batch-status')
def get_batch_status():
    """Get current batch processing status."""
    try:
        pending_posts = dashboard.get_pending_posts()
        return jsonify({
            'pending_count': len(pending_posts),
            'batch_size': 5,
            'has_more_posts': len(pending_posts) == 5
        })
    except Exception as e:
        logger.error(f"Failed to get batch status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/pending-posts')
def api_pending_posts():
    """API endpoint for pending posts."""
    return jsonify(dashboard.get_pending_posts())

@app.route('/api/optimize-post/<int:post_id>', methods=['POST'])
def api_optimize_post(post_id):
    """Optimize a specific post."""
    try:
        # Get post data
        post = dashboard.wp_client.get_post(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404

        # Extract post data
        title = post['title']['rendered']
        excerpt = post['excerpt']['rendered']
        content = post['content']['rendered']
        tags = dashboard.wp_client.get_post_tags(post_id)

        # Mark post as being processed
        dashboard.mark_post_processing(post_id, title)

        # Get media data from TMDB
        media_data = dashboard.tmdb_client.find_media_for_post(title, content)

        # Optimize content with Gemini including media
        optimized_content = dashboard.gemini_client.optimize_content(
            title=title,
            excerpt=excerpt,
            content=content,
            tags=tags,
            domain=dashboard.config.wordpress_domain,
            media_data=media_data
        )

        if optimized_content:
            # Update WordPress post
            success = dashboard.wp_client.update_post(
                post_id=post_id,
                title=optimized_content['title'],
                excerpt=optimized_content['excerpt'],
                content=optimized_content['content']
            )

            if success:
                dashboard.log_optimization(post_id, title, 'success', seo_score=85)
                return jsonify({'success': True, 'message': 'Post optimized successfully'})
            else:
                dashboard.log_optimization(post_id, title, 'failed', 'Failed to update WordPress post')
                return jsonify({'error': 'Failed to update post in WordPress'}), 500
        else:
            error_msg = "Falha ao otimizar com a Gemini. Causas comuns: chave de API inválida ou quota diária excedida. Verifique os logs do terminal para o erro exato."
            dashboard.log_optimization(post_id, title, 'failed', error_msg)
            return jsonify({'error': error_msg}), 500

    except Exception as e:
        logger.error(f"Failed to optimize post {post_id}: {e}")
        dashboard.log_optimization(post_id, 'Unknown', 'failed', str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/api/mark-success/<int:post_id>', methods=['POST'])
def api_mark_success(post_id):
    """Manually mark a post's optimization as successful."""
    try:
        # Fetch post from WordPress to get the title, as it might not be in the DB
        # if the failure happened very early.
        post = dashboard.wp_client.get_post(post_id)
        if not post:
            return jsonify({'error': 'Post not found in WordPress'}), 404
        
        title = post['title']['rendered']
        
        # Log the success status in the dashboard's database.
        # This adds a new 'success' record, which will override previous statuses
        # in the dashboard logic.
        dashboard.log_optimization(
            post_id=post_id,
            title=title,
            status='success',
            recommendations='Manually marked as successful.'
        )
        
        logger.info(f"Post ID {post_id} ('{title}') manually marked as successful.")
        return jsonify({'success': True, 'message': f'Post {post_id} marked as successful.'})

    except Exception as e:
        logger.error(f"Failed to manually mark post {post_id} as successful: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/system-status')
def api_system_status():
    """API endpoint for system status check."""
    try:
        wp_status = dashboard.wp_client.test_connection()
        gemini_status_details = dashboard.gemini_client.test_connection()
        tmdb_status = dashboard.tmdb_client.test_connection()

        return jsonify({
            'wordpress': wp_status,
            'gemini': gemini_status_details,
            'tmdb': tmdb_status,
            'database': os.path.exists(dashboard.db_path),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)