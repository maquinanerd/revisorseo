"""
Google Gemini 1.5 Pro client for content optimization.
"""

import json
import logging
import re
from typing import Dict, List, Optional
from datetime import datetime, date
import os

import google.generativeai as genai

logger = logging.getLogger(__name__)


class GeminiClient:
    """Client for interacting with Google Gemini 1.5 Pro API."""

    def __init__(self, api_key: str, backup_keys: list = None):
        """
        Initialize Gemini client with backup keys support.

        Args:
            api_key: Primary Google Gemini API key
            backup_keys: List of all available API keys (including primary)
        """
        self.api_keys = backup_keys if backup_keys else [api_key]
        self.current_key_index = 0
        self.current_api_key = self.api_keys[0]
        
        genai.configure(api_key=self.current_api_key)
        self.model = "gemini-1.5-flash"
        self.quota_file = "gemini_quota.json"
        self.max_daily_requests = 45  # Leave some buffer from 50 limit
        logger.info(f"Gemini client initialized with {len(self.api_keys)} API key(s)")

    def _load_quota_data(self) -> dict:
        """Load quota usage data from file."""
        try:
            if os.path.exists(self.quota_file):
                with open(self.quota_file, 'r') as f:
                    data = json.load(f)
                    # Reset if it's a new day
                    if data.get('date') != str(date.today()):
                        return {'date': str(date.today()), 'requests': 0}
                    return data
            else:
                return {'date': str(date.today()), 'requests': 0}
        except Exception as e:
            logger.error(f"Error loading quota data: {e}")
            return {'date': str(date.today()), 'requests': 0}

    def _save_quota_data(self, data: dict):
        """Save quota usage data to file."""
        try:
            with open(self.quota_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Error saving quota data: {e}")

    def _can_make_request(self) -> bool:
        """Check if we can make a request without exceeding quota."""
        quota_data = self._load_quota_data()
        return quota_data['requests'] < self.max_daily_requests

    def _increment_quota_usage(self):
        """Increment quota usage counter."""
        quota_data = self._load_quota_data()
        quota_data['requests'] += 1
        self._save_quota_data(quota_data)

    def _switch_to_backup_key(self):
        """Switch to the next available API key."""
        logger.info(f"DEBUG: Current key index: {self.current_key_index}, Total keys: {len(self.api_keys)}")
        if len(self.api_keys) > 1 and self.current_key_index < len(self.api_keys) - 1:
            self.current_key_index += 1
            self.current_api_key = self.api_keys[self.current_key_index]
            genai.configure(api_key=self.current_api_key)
            logger.info(f"✅ Switched to backup API key #{self.current_key_index + 1} - {self.current_api_key[:20]}...")
            return True
        else:
            logger.warning(f"❌ No backup key available. Keys: {len(self.api_keys)}, Current index: {self.current_key_index}")
            return False

    def _create_seo_prompt(self, title: str, excerpt: str, content: str, tags: List[str], domain: str, 
                          media_data: Optional[Dict] = None) -> str:
        """Create the SEO optimization prompt for Gemini."""
        tags_text = ", ".join(tags) if tags else ""

        prompt = f"""Você é um jornalista especialista em cultura pop, cinema e séries. Sua tarefa é revisar o conteúdo abaixo para SEO no Google News, sem alterar a essência do texto. A revisão deve seguir as diretrizes abaixo:

1. Otimize o título, mantendo a clareza e adicionando palavras-chave relevantes para melhorar o desempenho nos mecanismos de busca.
2. Reescreva o resumo (excerpt) tornando-o mais atrativo e informativo, com foco em engajamento e SEO.
3. Reestruture o conteúdo completo sem mudar o sentido original:
   - Separe parágrafos muito grandes em blocos menores e mais escaneáveis.
   - Mantenha o tom jornalístico e informativo.
4. Destaque com tags HTML <b>negrito</b> os principais nomes, termos e expressões importantes (títulos de filmes, nomes de personagens, diretores, datas etc.).
5. Insira links internos em HTML em termos relacionados a outras matérias, com base nas tags fornecidas. Use esta estrutura de link:
   <a href="https://{domain}/tag/NOME-DA-TAG">Texto âncora</a>

Exemplo:
<b><a href="https://{domain}/tag/stranger-things">Stranger Things</a></b>

Importante: 
- Use APENAS HTML: <b> para negrito e <a href=""> para links
- NÃO use markdown (**texto** ou [texto](link))
- Inclua imagens e trailers quando disponíveis (dados fornecidos abaixo)
- Para imagens: use <img src="URL" alt="DESCRIÇÃO" style="width:100%;max-width:500px;height:auto;margin:10px 0;">
- Para trailers: use <iframe width="560" height="315" src="https://www.youtube.com/embed/ID_DO_VIDEO" frameborder="0" allowfullscreen style="margin:10px 0;"></iframe>
- Não mude o conteúdo nem o sentido original, apenas melhore a estrutura, o SEO e a escaneabilidade para o Google News.

## MÍDIA DISPONÍVEL:
{self._format_media_data(media_data) if media_data else "Nenhuma mídia encontrada"}

## CONTEÚDO ORIGINAL:

**Título:** {title}

**Resumo:** {excerpt}

**Tags disponíveis:** {tags_text}

**Conteúdo:**
{content}

## FORMATO DA RESPOSTA (responda EXATAMENTE neste formato):

## Novo Título:
(título otimizado)

## Novo Resumo:
(resumo otimizado)

## Novo Conteúdo:
(conteúdo revisado com parágrafos curtos, negrito e links internos)"""

        return prompt

    def _format_media_data(self, media_data: Dict) -> str:
        """Format media data for inclusion in the prompt."""
        if not media_data:
            return "Nenhuma mídia disponível"

        formatted = []

        # Add images
        if media_data.get('images'):
            formatted.append("### IMAGENS DISPONÍVEIS:")
            for img in media_data['images']:
                formatted.append(f"- {img['title']} ({img['type']}): {img['url']} - Alt: {img['alt']}")

        # Add trailers
        if media_data.get('trailers'):
            formatted.append("\n### TRAILERS DISPONÍVEIS:")
            for trailer in media_data['trailers']:
                formatted.append(f"- {trailer['title']}: YouTube ID = {trailer['youtube_key']}")

        return "\n".join(formatted) if formatted else "Nenhuma mídia disponível"

    def _parse_response(self, response_text: str) -> Optional[Dict[str, str]]:
        """Parse the Gemini response to extract title, excerpt, and content."""
        try:
            # Use regex to extract sections
            title_match = re.search(r'## Novo Título:\s*\n(.*?)(?=\n## |$)', response_text, re.DOTALL)
            excerpt_match = re.search(r'## Novo Resumo:\s*\n(.*?)(?=\n## |$)', response_text, re.DOTALL)
            content_match = re.search(r'## Novo Conteúdo:\s*\n(.*?)$', response_text, re.DOTALL)

            if not all([title_match, excerpt_match, content_match]):
                logger.error("Could not parse all sections from Gemini response")
                return None

            # Check if matches have groups before accessing them
            if title_match and excerpt_match and content_match:
                result = {
                    'title': title_match.group(1).strip(),
                    'excerpt': excerpt_match.group(1).strip(),
                    'content': content_match.group(1).strip()
                }

                # Basic validation
                if not all(result.values()):
                    logger.error("One or more sections are empty in Gemini response")
                    return None

                return result
            else:
                logger.error("Failed to extract content sections from Gemini response")
                return None

        except Exception as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            return None

    def optimize_content(self, title: str, excerpt: str, content: str, tags: List[str], domain: str, 
                        media_data: Optional[Dict] = None) -> Optional[Dict[str, str]]:
        """
        Optimize content using Gemini 1.5 Pro.

        Args:
            title: Original post title
            excerpt: Original post excerpt
            content: Original post content
            tags: List of post tags
            domain: Website domain for internal links

        Returns:
            Dictionary with optimized title, excerpt, and content, or None if failed
        """
        import time

        try:
            # Check quota before making request
            if not self._can_make_request():
                quota_data = self._load_quota_data()
                logger.warning(f"Daily quota exceeded. Used {quota_data['requests']}/{self.max_daily_requests} requests today")
                return None

            # Create the prompt with media data
            prompt = self._create_seo_prompt(title, excerpt, content, tags, domain, media_data)

            # Make request to Gemini with retry logic
            model = genai.GenerativeModel(self.model)

            max_retries = 5
            base_delay = 10

            for attempt in range(max_retries):
                try:
                    # Add delay before each attempt
                    if attempt > 0:
                        delay = base_delay * (2 ** attempt)  # Exponential backoff
                        logger.info(f"Waiting {delay} seconds before retry attempt {attempt}")
                        time.sleep(delay)

                    response = model.generate_content(
                        prompt,
                        generation_config={
                            'temperature': 0.3,
                            'max_output_tokens': 4000,
                        }
                    )

                    if not response.text:
                        logger.error("Empty response from Gemini")
                        return None

                    logger.info("Received response from Gemini")

                    # Parse the response
                    parsed_result = self._parse_response(response.text)

                    if parsed_result:
                        logger.info("Successfully parsed Gemini response")
                        # Increment quota usage on successful request
                        self._increment_quota_usage()
                        return parsed_result
                    else:
                        logger.error("Failed to parse Gemini response")
                        return None

                except Exception as e:
                    error_str = str(e)
                    if "429" in error_str and "quota" in error_str.lower():
                        logger.warning(f"Quota exceeded on key #{self.current_key_index + 1}")
                        
                        # Try to switch to backup key
                        if self._switch_to_backup_key():
                            logger.info("Retrying with backup API key")
                            continue
                        
                        # If no backup key available, wait
                        import re
                        retry_match = re.search(r'retry_delay.*?seconds:\s*(\d+)', error_str)
                        wait_time = int(retry_match.group(1)) if retry_match else 60

                        logger.warning(f"No backup key available. Waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
                        if attempt < max_retries - 1:
                            time.sleep(wait_time)
                            continue
                        else:
                            logger.error("Max retries reached for quota exceeded error")
                            return None
                    else:
                        logger.error(f"Failed to optimize content with Gemini (attempt {attempt + 1}): {e}")
                        if attempt < max_retries - 1:
                            time.sleep(2)  # Short delay for other errors
                            continue
                        else:
                            return None

        except Exception as e:
            logger.error(f"Failed to optimize content with Gemini: {e}")
            return None

    def test_connection(self) -> bool:
        """Test the Gemini API connection."""
        logger.info("Testing Gemini API connection...")
        try:
            # A lightweight call to test authentication and connectivity.
            model = genai.GenerativeModel(self.model)
            response = model.generate_content(
                "Olá",
                generation_config={'max_output_tokens': 5}
            )
            if response.text:
                logger.info("✅ Gemini API connection test successful.")
                return True
            logger.error("Gemini API connection test failed: received empty response.")
            return False
        except Exception as e:
            logger.error(f"❌ Gemini API connection test failed: {e}")
            return False