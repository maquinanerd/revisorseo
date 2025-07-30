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
        return self._extract_potential_titles(content)

    def _extract_main_title_from_post(self, post_title: str) -> str:
        """Extract the main title from WordPress post title with improved intelligence."""
        import html
        clean_title = html.unescape(post_title)
        
        # Known franchise patterns (highest priority)
        franchise_patterns = [
            r'\b(The Walking Dead|Walking Dead)\b',
            r'\b(Stranger Things)\b',
            r'\b(Game of Thrones)\b',
            r'\b(House of the Dragon)\b',
            r'\b(The Last of Us)\b',
            r'\b(Marvel|MCU)\b',
            r'\b(DC Comics|DC Universe)\b',
            r'\b(Star Wars)\b',
            r'\b(Harry Potter)\b',
            r'\b(Breaking Bad|Better Call Saul)\b',
            r'\b(The Boys)\b',
            r'\b(Wednesday|Wandinha)\b',
            r'\b(Euphoria)\b',
            r'\b(Avatar)\b',
            r'\b(John Wick)\b',
            r'\b(Fast (?:and|&) Furious|Velozes e Furiosos)\b',
            r'\b(Mission Impossible|Missão Impossível)\b'
        ]
        
        # Check for known franchises first
        for pattern in franchise_patterns:
            match = re.search(pattern, clean_title, re.IGNORECASE)
            if match:
                title = match.group(1)
                # Normalize known titles
                title_map = {
                    'Walking Dead': 'The Walking Dead',
                    'Marvel': 'Marvel',
                    'MCU': 'Marvel',
                    'DC Comics': 'DC',
                    'DC Universe': 'DC',
                    'Velozes e Furiosos': 'Fast and Furious',
                    'Missão Impossível': 'Mission Impossible'
                }
                title = title_map.get(title, title)
                logger.info(f"Found franchise title: '{title}'")
                return title
        
        # Enhanced patterns for specific content
        enhanced_patterns = [
            # Title in quotes
            r'"([^"]{3,50})"',
            r"'([^']{3,50})'",
            # Title after "série" or "filme"
            r'(?:série|filme|season|temporada)\s+"?([A-Z][^",.!?]{2,40})"?',
            # Title followed by colon and description
            r'^([^:]{3,50}):',
            # Title in parentheses or brackets
            r'\(([^)]{3,50})\)',
            r'\[([^\]]{3,50})\]',
            # Title at the beginning (up to common separators)
            r'^([A-Z][A-Za-z0-9\s\-\.]{2,40})(?:\s*[:\-–—]|\s*\(|\s*\[)',
        ]
        
        for pattern in enhanced_patterns:
            match = re.search(pattern, clean_title)
            if match:
                title = match.group(1).strip()
                if self._is_valid_title(title):
                    logger.info(f"Extracted title using pattern: '{title}'")
                    return title
        
        # Fallback: intelligent word extraction
        words = clean_title.split()
        if len(words) >= 2:
            meaningful_words = []
            for word in words:
                if len(meaningful_words) >= 4:  # Reduced limit
                    break
                if self._is_meaningful_word(word) and len(word) > 2:
                    meaningful_words.append(word)
            
            if len(meaningful_words) >= 2:
                extracted = ' '.join(meaningful_words)
                if self._is_valid_title(extracted):
                    logger.info(f"Extracted title from meaningful words: '{extracted}'")
                    return extracted
        
        return ""

    def _is_valid_title(self, title: str) -> bool:
        """Check if a title is valid for TMDB search with enhanced filtering."""
        if not title or len(title) < 3 or len(title) > 50:
            return False
        
        # Enhanced skip phrases - more comprehensive filtering
        skip_phrases = [
            'nova temporada', 'surpreende', 'rotten tomatoes', 'temporada de',
            'filme de', 'série de', 'nova série', 'novo filme', 'trailer',
            'primeira temporada', 'segunda temporada', 'terceira temporada',
            'maiores reviravoltas', 'da amc', 'de grandes', 'grandes vilões',
            'vilões implacáveis', 'implacáveis', 'reviravoltas', 'maiores',
            'nova fase', 'novo episódio', 'episódio de', 'temporada final',
            'final de', 'estreia de', 'lançamento de', 'crítica de',
            'análise de', 'review de', 'comentário sobre', 'opinião sobre',
            'sobre a', 'sobre o', 'em alta', 'em cartaz', 'nos cinemas',
            'na netflix', 'na amazon', 'na hbo', 'no disney', 'streaming',
            'plataforma de', 'disponível em', 'assistir em', 'onde assistir'
        ]
        
        title_lower = title.lower().strip()
        
        # Check for skip phrases
        for phrase in skip_phrases:
            if phrase in title_lower:
                logger.debug(f"Skipping title '{title}' - contains skip phrase: '{phrase}'")
                return False
        
        # Must contain at least one letter
        if not re.search(r'[A-Za-z]', title):
            return False
            
        # Skip if mostly numbers or symbols
        alpha_chars = len(re.findall(r'[A-Za-z]', title))
        if alpha_chars < len(title) * 0.5:  # At least 50% letters
            return False
        
        # Skip generic words
        generic_words = {'the', 'a', 'an', 'and', 'or', 'but', 'of', 'in', 'on', 'at', 'to', 'for', 'with', 'by'}
        words = title_lower.split()
        meaningful_words = [w for w in words if w not in generic_words and len(w) > 2]
        
        if len(meaningful_words) < 1:
            return False
            
        logger.debug(f"Title '{title}' passed validation")
        return True

    def _is_meaningful_word(self, word: str) -> bool:
        """Check if a word is meaningful for title extraction."""
        word_lower = word.lower()
        stop_words = {
            'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'o', 'a', 'e', 'de', 'da', 'do', 'em', 'com',
            'para', 'por', 'nova', 'novo', 'uma', 'um', 'sua', 'seu'
        }
        return word_lower not in stop_words and len(word) > 1

    def _extract_potential_titles(self, content: str) -> List[str]:
        """Extract potential movie/TV show titles from content with improved accuracy."""
        
        # First, look for known franchises and exact matches
        franchise_patterns = [
            r'\b(The Walking Dead|Walking Dead)\b',
            r'\b(Stranger Things)\b',
            r'\b(Game of Thrones)\b',
            r'\b(House of the Dragon)\b',
            r'\b(The Last of Us)\b',
            r'\b(Breaking Bad|Better Call Saul)\b',
            r'\b(The Boys)\b',
            r'\b(Wednesday|Wandinha)\b',
            r'\b(Euphoria)\b',
            r'\b(Avatar)\b',
            r'\b(John Wick)\b',
            r'\b(Fast (?:and|&) Furious|Velozes e Furiosos)\b',
            r'\b(Mission Impossible|Missão Impossível)\b'
        ]
        
        titles = []
        
        # Priority 1: Known franchises
        for pattern in franchise_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if match and len(match) > 2:
                    # Normalize titles
                    if 'walking dead' in match.lower():
                        title = 'The Walking Dead'
                    elif 'velozes e furiosos' in match.lower():
                        title = 'Fast and Furious'
                    elif 'missão impossível' in match.lower():
                        title = 'Mission Impossible'
                    else:
                        title = match
                    
                    if title not in titles:
                        titles.append(title)
        
        # Priority 2: Specific content patterns (only if no franchises found)
        if not titles:
            enhanced_patterns = [
                # Titles in quotes
                r'"([A-Z][^"]{3,40})"',
                r"'([A-Z][^']{3,40})'",
                # Titles after keywords
                r'(?:filme|série|season|temporada)\s+["\']?([A-Z][A-Za-z\s]{2,35})["\']?',
                # Titles in bold tags
                r'<b>\s*([A-Z][A-Za-z\s]{3,35})\s*</b>',
                # Titles with years
                r'([A-Z][A-Za-z\s]{3,35})\s*\(\d{4}\)',
                # Known studios/networks followed by titles
                r'(?:Marvel|DC|Netflix|HBO|Amazon|Disney)\s+([A-Z][A-Za-z\s]{3,35})',
            ]
            
            for pattern in enhanced_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        title = ' '.join([part for part in match if part]).strip()
                    else:
                        title = match.strip()
                    
                    # Clean title
                    title = re.sub(r'[^\w\s\-:()]', ' ', title)
                    title = ' '.join(title.split())
                    
                    if self._is_valid_title(title) and title not in titles:
                        titles.append(title)
        
        logger.info(f"Extracted potential titles from content: {titles}")
        return titles[:2]  # Limit to 2 most relevant titles

    def find_media_for_post(self, title: str, content: str, categories: List[Dict] = None) -> Dict[str, Any]:
        """
        Find relevant media (images, trailers) for a post.

        Args:
            title: Post title
            content: Post content
            categories: Post categories with id, name, slug

        Returns:
            Dictionary with found media data
        """
        media_data = {
            'images': [],
            'trailers': [],
            'found_titles': []
        }

        # Determine search priority based on categories
        is_movie_category = any(cat.get('id') == 24 for cat in (categories or []))
        is_tv_category = any(cat.get('id') == 21 for cat in (categories or []))
        
        logger.info(f"Category analysis - Movies: {is_movie_category}, TV: {is_tv_category}")

        # Extract and clean the main title from post title
        main_title = self._extract_main_title_from_post(title)
        logger.info(f"Extracted main title: {main_title}")

        # Extract potential titles from content
        content_titles = self.extract_titles_from_content(content)
        
        # Prioritize titles: main title first, then content titles
        all_titles = [main_title] + content_titles if main_title else content_titles
        potential_titles = list(dict.fromkeys(all_titles))  # Remove duplicates while preserving order
        
        logger.info(f"Searching for titles: {potential_titles}")

        for potential_title in potential_titles[:3]:  # Limit to 3 titles
            # Search based on category priority
            movie = None
            tv_show = None
            
            if is_movie_category:
                # Search movies first for movie category
                movie = self.search_movie(potential_title)
                if not movie and not is_tv_category:
                    # Try TV as fallback only if not specifically TV category
                    tv_show = self.search_tv_show(potential_title)
            elif is_tv_category:
                # Search TV shows first for TV category
                tv_show = self.search_tv_show(potential_title)
                if not tv_show:
                    # Try movies as fallback
                    movie = self.search_movie(potential_title)
            else:
                # No specific category, try both (movies first)
                movie = self.search_movie(potential_title)
                if not movie:
                    tv_show = self.search_tv_show(potential_title)
            
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