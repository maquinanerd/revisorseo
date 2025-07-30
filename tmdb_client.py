"""
TMDB (The Movie Database) API client for fetching movie/TV show images and trailers.
"""

import requests
import logging
import re
from typing import Dict, List, Optional, Any
from urllib.parse import quote

logger = logging.getLogger(__name__)


class TMDBClient:
    """Client for interacting with TMDB API."""
    
    def __init__(self, api_key: str, read_token: str):
        """
        Initialize TMDB client.
        
        Args:
            api_key: TMDB API key
            read_token: TMDB read access token
        """
        self.api_key = api_key
        self.base_url = "https://api.themoviedb.org/3"
        self.image_base_url = "https://image.tmdb.org/t/p"
        
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {read_token}',
            'Content-Type': 'application/json;charset=utf-8',
            'User-Agent': 'WordPress-SEO-Optimizer/1.0'
        })
        
        logger.info("TMDB client initialized")
    
    def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make a request to TMDB API."""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"TMDB API request failed: {url} - {e}")
            return None
    
    def search_movie(self, title: str, year: Optional[int] = None) -> Optional[Dict]:
        """
        Search for a movie by title.
        
        Args:
            title: Movie title to search for
            year: Optional release year for better matching
            
        Returns:
            Movie data or None if not found
        """
        params = {
            'query': title,
            'language': 'pt-BR',
            'include_adult': 'false'
        }
        
        if year:
            params['year'] = year
        
        result = self._make_request('search/movie', params)
        
        if result and result.get('results'):
            # Return the first (most relevant) result
            movie = result['results'][0]
            logger.info(f"Found movie: {movie.get('title')} ({movie.get('release_date', 'Unknown')})")
            return movie
        
        logger.warning(f"No movie found for title: {title}")
        return None
    
    def search_tv_show(self, title: str, year: Optional[int] = None) -> Optional[Dict]:
        """
        Search for a TV show by title.
        
        Args:
            title: TV show title to search for
            year: Optional first air year for better matching
            
        Returns:
            TV show data or None if not found
        """
        params = {
            'query': title,
            'language': 'pt-BR',
            'include_adult': 'false'
        }
        
        if year:
            params['first_air_date_year'] = year
        
        result = self._make_request('search/tv', params)
        
        if result and result.get('results'):
            # Return the first (most relevant) result
            tv_show = result['results'][0]
            logger.info(f"Found TV show: {tv_show.get('name')} ({tv_show.get('first_air_date', 'Unknown')})")
            return tv_show
        
        logger.warning(f"No TV show found for title: {title}")
        return None
    
    def get_movie_videos(self, movie_id: int) -> List[Dict]:
        """Get videos (trailers) for a movie."""
        result = self._make_request(f'movie/{movie_id}/videos', {'language': 'pt-BR'})
        
        if result and result.get('results'):
            # Filter for trailers and teasers, prioritize Portuguese
            videos = []
            for video in result['results']:
                if video.get('type') in ['Trailer', 'Teaser'] and video.get('site') == 'YouTube':
                    videos.append({
                        'key': video['key'],
                        'name': video['name'],
                        'type': video['type'],
                        'language': video.get('iso_639_1', 'en'),
                        'url': f"https://www.youtube.com/watch?v={video['key']}"
                    })
            return videos
        
        return []
    
    def get_tv_videos(self, tv_id: int) -> List[Dict]:
        """Get videos (trailers) for a TV show."""
        result = self._make_request(f'tv/{tv_id}/videos', {'language': 'pt-BR'})
        
        if result and result.get('results'):
            # Filter for trailers and teasers
            videos = []
            for video in result['results']:
                if video.get('type') in ['Trailer', 'Teaser'] and video.get('site') == 'YouTube':
                    videos.append({
                        'key': video['key'],
                        'name': video['name'],
                        'type': video['type'],
                        'language': video.get('iso_639_1', 'en'),
                        'url': f"https://www.youtube.com/watch?v={video['key']}"
                    })
            return videos
        
        return []
    
    def get_image_url(self, path: str, size: str = 'w500') -> str:
        """
        Get full URL for an image path.
        
        Args:
            path: Image path from TMDB
            size: Image size (w92, w154, w185, w342, w500, w780, original)
            
        Returns:
            Full image URL
        """
        if not path:
            return ""
        
        return f"{self.image_base_url}/{size}{path}"
    
    def extract_titles_from_content(self, content: str) -> List[str]:
        """
        Extract potential movie/TV show titles from content.
        
        Args:
            content: Post content to analyze
            
        Returns:
            List of potential titles found
        """
        # Common patterns for movie/TV titles in Portuguese content
        patterns = [
            # Titles in quotes
            r'"([^"]+)"',
            r'\'([^\']+)\'',
            # Titles after common phrases
            r'filme\s+([A-Z][^,.!?]+)',
            r'série\s+([A-Z][^,.!?]+)',
            r'temporada\s+\d+\s+de\s+([A-Z][^,.!?]+)',
            # Titles in bold tags
            r'<b>([^<]+)</b>',
            # Titles in italics
            r'<i>([^<]+)</i>',
            # Capitalized words that might be titles
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]*)*)\b'
        ]
        
        titles = []
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                # Clean up the title
                title = match.strip()
                # Filter out common words that aren't titles
                if (len(title) > 3 and 
                    title not in ['The', 'A', 'An', 'O', 'A', 'Os', 'As', 'Um', 'Uma'] and
                    not title.isdigit()):
                    titles.append(title)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_titles = []
        for title in titles:
            if title.lower() not in seen:
                seen.add(title.lower())
                unique_titles.append(title)
        
        return unique_titles[:5]  # Limit to first 5 potential titles
    
    def find_media_for_post(self, title: str, content: str) -> Dict[str, Any]:
        """
        Find relevant media (images, trailers) for a post.
        
        Args:
            title: Post title
            content: Post content
            
        Returns:
            Dictionary with found media data
        """
        media_data = {
            'images': [],
            'trailers': [],
            'found_titles': []
        }
        
        # Extract potential titles from content
        potential_titles = self.extract_titles_from_content(f"{title} {content}")
        
        for potential_title in potential_titles:
            # Try to find as movie first
            movie = self.search_movie(potential_title)
            if movie:
                media_data['found_titles'].append({
                    'title': movie['title'],
                    'type': 'movie',
                    'tmdb_id': movie['id']
                })
                
                # Add poster image
                if movie.get('poster_path'):
                    media_data['images'].append({
                        'url': self.get_image_url(movie['poster_path'], 'w500'),
                        'alt': f"Poster do filme {movie['title']}",
                        'type': 'poster',
                        'title': movie['title']
                    })
                
                # Add backdrop image
                if movie.get('backdrop_path'):
                    media_data['images'].append({
                        'url': self.get_image_url(movie['backdrop_path'], 'w780'),
                        'alt': f"Imagem do filme {movie['title']}",
                        'type': 'backdrop',
                        'title': movie['title']
                    })
                
                # Get trailers
                videos = self.get_movie_videos(movie['id'])
                for video in videos[:2]:  # Limit to 2 trailers per movie
                    media_data['trailers'].append({
                        'url': video['url'],
                        'title': f"Trailer: {movie['title']} - {video['name']}",
                        'type': video['type'],
                        'youtube_key': video['key']
                    })
                
                continue
            
            # Try to find as TV show
            tv_show = self.search_tv_show(potential_title)
            if tv_show:
                media_data['found_titles'].append({
                    'title': tv_show['name'],
                    'type': 'tv',
                    'tmdb_id': tv_show['id']
                })
                
                # Add poster image
                if tv_show.get('poster_path'):
                    media_data['images'].append({
                        'url': self.get_image_url(tv_show['poster_path'], 'w500'),
                        'alt': f"Poster da série {tv_show['name']}",
                        'type': 'poster',
                        'title': tv_show['name']
                    })
                
                # Add backdrop image
                if tv_show.get('backdrop_path'):
                    media_data['images'].append({
                        'url': self.get_image_url(tv_show['backdrop_path'], 'w780'),
                        'alt': f"Imagem da série {tv_show['name']}",
                        'type': 'backdrop',
                        'title': tv_show['name']
                    })
                
                # Get trailers
                videos = self.get_tv_videos(tv_show['id'])
                for video in videos[:2]:  # Limit to 2 trailers per TV show
                    media_data['trailers'].append({
                        'url': video['url'],
                        'title': f"Trailer: {tv_show['name']} - {video['name']}",
                        'type': video['type'],
                        'youtube_key': video['key']
                    })
        
        logger.info(f"Found {len(media_data['images'])} images and {len(media_data['trailers'])} trailers for post")
        return media_data
    
    def test_connection(self) -> bool:
        """Test TMDB API connection."""
        try:
            result = self._make_request('configuration')
            if result and 'images' in result:
                logger.info("TMDB API connection test successful")
                return True
            else:
                logger.error("TMDB API connection test failed - unexpected response")
                return False
                
        except Exception as e:
            logger.error(f"TMDB API connection test failed: {e}")
            return False