"""
Google Gemini 1.5 Pro client for content optimization.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional
from datetime import datetime, date
import os

import google.generativeai as genai

logger = logging.getLogger(__name__)


class GeminiClient:
    """Client for interacting with Google Gemini 1.5 Pro API."""

    def __init__(self, api_keys: List[str], 
                 temperature: float = 0.3, max_tokens: int = 4000):
        """
        Initialize Gemini client with backup keys support.

        Args:
            api_keys: List of all available API keys. The first is used as primary.
            temperature: The generation temperature.
            max_tokens: The maximum number of output tokens.
        """
        if not api_keys:
            raise ValueError("At least one Gemini API key must be provided.")
        self.api_keys = api_keys
        self.current_key_index = 0
        self.current_api_key = self.api_keys[0]
        
        genai.configure(api_key=self.current_api_key)
        self.model = "gemini-1.5-flash"
        self.quota_file = "gemini_quota.json"
        self.max_daily_requests = 45  # Leave some buffer from 50 limit
        
        # Generation configuration
        self.temperature = temperature
        self.max_output_tokens = max_tokens
        logger.info(f"Gemini client initialized with {len(self.api_keys)} API key(s): {[k[:8]+'...' for k in self.api_keys]}")

    def _load_quota_data(self) -> Dict:
        """Load quota usage data for all keys from file."""
        try:
            if os.path.exists(self.quota_file):
                with open(self.quota_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading quota data: {e}")
            return {}

    def _save_quota_data(self, all_data: Dict):
        """Save quota usage data for all keys to file."""
        try:
            with open(self.quota_file, 'w') as f:
                json.dump(all_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving quota data: {e}")

    def _can_make_request(self) -> bool:
        """Check if the current key can make a request without exceeding quota."""
        all_quota_data = self._load_quota_data()
        key_identifier = self.current_api_key[:12] # Use a portion of the key as identifier
        key_data = all_quota_data.get(key_identifier, {})

        # Reset if it's a new day for this specific key
        if key_data.get('date') != str(date.today()):
            key_data = {'date': str(date.today()), 'requests': 0}
            all_quota_data[key_identifier] = key_data
            self._save_quota_data(all_quota_data)

        can_request = key_data.get('requests', 0) < self.max_daily_requests
        if not can_request:
            logger.warning(f"Local quota exceeded for key {key_identifier}... ({key_data.get('requests', 0)}/{self.max_daily_requests})")
        return can_request

    def _increment_quota_usage(self):
        """Increment quota usage counter."""
        all_quota_data = self._load_quota_data()
        key_identifier = self.current_api_key[:12]
        
        # Get or initialize data for the current key
        key_data = all_quota_data.get(key_identifier, {'date': str(date.today()), 'requests': 0})
        
        # Ensure date is current before incrementing
        if key_data.get('date') != str(date.today()):
            key_data['date'] = str(date.today())
            key_data['requests'] = 0

        key_data['requests'] += 1
        all_quota_data[key_identifier] = key_data
        self._save_quota_data(all_quota_data)
        logger.info(f"Quota for key {key_identifier}... updated to {key_data['requests']}/{self.max_daily_requests}")
 
    def _set_active_key(self, key_index: int):
        """Set the active API key by its index and reconfigure the client."""
        if 0 <= key_index < len(self.api_keys):
            self.current_key_index = key_index
            self.current_api_key = self.api_keys[self.current_key_index]
            genai.configure(api_key=self.current_api_key)
            logger.info(f"Set active API key to #{self.current_key_index + 1} ({self.current_api_key[:8]}...).")
 
    def _switch_to_backup_key(self) -> bool:
        """Switch to the next available API key. Returns True if successful."""
        if self.current_key_index < len(self.api_keys) - 1:
            self._set_active_key(self.current_key_index + 1)
            return True
        logger.warning("No more backup keys available to switch to.")
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

        prompt = self._create_seo_prompt(title, excerpt, content, tags, domain, media_data)
        model = genai.GenerativeModel(self.model)
        max_retries_per_key = 3
        retry_delay = 5  # seconds

        # Loop through each available API key, starting from the current one
        for key_index in range(self.current_key_index, len(self.api_keys)):
            self._set_active_key(key_index)

            if not self._can_make_request():
                logger.warning(f"Local quota for key #{self.current_key_index + 1} is exceeded. Skipping.")
                continue

            # Retry loop for the current key
            for attempt in range(max_retries_per_key):
                try:
                    logger.info(f"Attempting to generate content with key #{self.current_key_index + 1} (Attempt {attempt + 1}/{max_retries_per_key})")
                    response = model.generate_content(
                        prompt,
                        generation_config={
                            'temperature': self.temperature, 
                            'max_output_tokens': self.max_output_tokens
                        }
                    )

                    if not response.text:
                        logger.error("Empty response from Gemini. Retrying...")
                        time.sleep(retry_delay)
                        continue

                    parsed_result = self._parse_response(response.text)
                    if parsed_result:
                        logger.info("Successfully generated and parsed content.")
                        self._increment_quota_usage()
                        return parsed_result
                    
                    logger.error("Failed to parse Gemini response. Retrying...")
                    time.sleep(retry_delay)

                except Exception as e:
                    error_str = str(e).lower()
                    wait_time = retry_delay # Default wait time

                    if "429" in error_str and "quota" in error_str:
                        # Try to parse the suggested retry delay from the API error
                        retry_match = re.search(r'retry_delay.*?seconds:\s*(\d+)', error_str)
                        if retry_match:
                            wait_time = int(retry_match.group(1)) + 1 # Add a small buffer
                            logger.warning(f"API quota exceeded. API suggests waiting {wait_time} seconds.")
                        else:
                            wait_time = 60 # Fallback if delay is not specified
                            logger.warning(f"API quota exceeded. Waiting for {wait_time} seconds as a fallback.")
                        
                        time.sleep(wait_time)
                        break  # Break inner retry loop, move to the next key

                    logger.error(f"Error on attempt {attempt + 1} with key #{self.current_key_index + 1}: {e}")
                    if attempt < max_retries_per_key - 1:
                        time.sleep(wait_time)
                    else:
                        logger.error(f"All retries failed for key #{self.current_key_index + 1}.")
            # This point is reached if the key's retries are exhausted or quota was hit.
            # The outer loop will now proceed to the next key.

        logger.error("All API keys have been tried and failed. Could not optimize content.")
        return None

    def test_connection(self) -> Dict[str, Any]:
        """
        Test the Gemini API connection for all available keys.
        Returns a dictionary with the overall status and individual key statuses.
        """
        logger.info("Testing Gemini API connection...")
        original_key_index = self.current_key_index
        key_statuses = []
        successful_connections = 0

        for idx, key in enumerate(self.api_keys):
            status_entry = {'key': f"Key #{idx+1} ({key[:8]}...)", 'status': 'failed'}
            try:
                genai.configure(api_key=key)
                model = genai.GenerativeModel(self.model)
                response = model.generate_content("Olá", generation_config={'max_output_tokens': 5})
                if response.text:
                    status_entry['status'] = 'ok'
                    successful_connections += 1
                else:
                    status_entry['error'] = "Empty response"
            except Exception as e:
                error_str = str(e)
                if "429" in error_str and "quota" in error_str.lower():
                    status_entry['status'] = 'quota_exceeded'
                    status_entry['error'] = "Quota Exceeded"
                else:
                    status_entry['error'] = "Invalid Key or API Error"
            key_statuses.append(status_entry)

        # Restore original key configuration
        self._set_active_key(original_key_index)

        overall_status = 'failed'
        if successful_connections == len(self.api_keys):
            overall_status = 'ok'
        elif successful_connections > 0:
            overall_status = 'partial'

        return {'overall_status': overall_status, 'keys': key_statuses}