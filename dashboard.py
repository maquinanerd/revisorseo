#!/usr/bin/env python3
"""
Visual SEO Recommendation Dashboard for WordPress SEO Optimizer.
Provides a web interface to monitor and manage SEO optimization status.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from flask import Flask, render_template, jsonify, request
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
            password=self.config.wordpress_password
        )
        self.gemini_client = GeminiClient(api_key=self.config.gemini_api_key)
        self.tmdb_client = TMDBClient(
            api_key=self.config.tmdb_api_key,
            read_token=self.config.tmdb_read_token
        )
        self.db_path = 'seo_dashboard.db'
        self.init_database()
        
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
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data."""
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
            
            return {
                'recent_optimizations': recent_optimizations,
                'weekly_metrics': weekly_metrics,
                'summary': {
                    'total_posts': summary[0] or 0,
                    'optimized_posts': summary[1] or 0,
                    'failed_posts': summary[2] or 0,
                    'success_rate': (summary[1] / summary[0] * 100) if summary[0] > 0 else 0
                }
            }
    
    def get_pending_posts(self) -> List[Dict[str, Any]]:
        """Get posts that need optimization."""
        try:
            # Get recent posts by João
            since_date = (datetime.now() - timedelta(days=7)).isoformat()
            posts = self.wp_client.get_posts_by_author(
                author_id=6,  # João's author ID
                since=since_date,
                per_page=50
            )
            
            # Check which posts haven't been optimized
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT DISTINCT post_id FROM optimization_history 
                    WHERE status = 'success'
                ''')
                optimized_post_ids = {row[0] for row in cursor.fetchall()}
            
            pending_posts = []
            for post in posts:
                if post['id'] not in optimized_post_ids:
                    pending_posts.append({
                        'id': post['id'],
                        'title': post['title']['rendered'],
                        'date': post['date'],
                        'status': post['status'],
                        'link': post['link']
                    })
            
            return pending_posts
            
        except Exception as e:
            logger.error(f"Failed to get pending posts: {e}")
            return []

# Flask Web Application
app = Flask(__name__)
app.secret_key = os.urandom(24)

dashboard = SEODashboard()

@app.route('/')
def index():
    """Main dashboard page."""
    data = dashboard.get_dashboard_data()
    pending_posts = dashboard.get_pending_posts()
    return render_template('dashboard.html', 
                         dashboard_data=data, 
                         pending_posts=pending_posts)

@app.route('/api/dashboard-data')
def api_dashboard_data():
    """API endpoint for dashboard data."""
    return jsonify(dashboard.get_dashboard_data())

@app.route('/api/pending-posts')
def api_pending_posts():
    """API endpoint for pending posts."""
    return jsonify(dashboard.get_pending_posts())

@app.route('/api/optimize-post/<int:post_id>', methods=['POST'])
def api_optimize_post(post_id):
    """API endpoint to trigger optimization of a specific post."""
    try:
        # Get post details
        post = dashboard.wp_client.get_post(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        # Extract post data
        title = post['title']['rendered']
        excerpt = post['excerpt']['rendered']
        content = post['content']['rendered']
        tags = dashboard.wp_client.get_post_tags(post_id)
        
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
            dashboard.log_optimization(post_id, title, 'failed', 'Failed to get optimized content from Gemini')
            return jsonify({'error': 'Failed to optimize content with Gemini'}), 500
            
    except Exception as e:
        logger.error(f"Failed to optimize post {post_id}: {e}")
        dashboard.log_optimization(post_id, 'Unknown', 'failed', str(e))
        return jsonify({'error': str(e)}), 500

@app.route('/api/system-status')
def api_system_status():
    """API endpoint for system status check."""
    try:
        wp_status = dashboard.wp_client.test_connection()
        gemini_status = dashboard.gemini_client.test_connection()
        tmdb_status = dashboard.tmdb_client.test_connection()
        
        return jsonify({
            'wordpress': wp_status,
            'gemini': gemini_status,
            'tmdb': tmdb_status,
            'database': os.path.exists(dashboard.db_path),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Update daily metrics on startup
    dashboard.update_daily_metrics()
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)