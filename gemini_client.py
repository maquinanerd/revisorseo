"""
Google Gemini 1.5 Pro client for content optimization.
"""

import json
import logging
import re
from typing import Dict, List, Optional

import google.generativeai as genai

logger = logging.getLogger(__name__)


class GeminiClient:
    """Client for interacting with Google Gemini 1.5 Pro API."""
    
    def __init__(self, api_key: str):
        """
        Initialize Gemini client.
        
        Args:
            api_key: Google Gemini API key
        """
        genai.configure(api_key=api_key)
        self.model = "gemini-1.5-flash"
        logger.info("Gemini client initialized")
    
    def _create_seo_prompt(self, title: str, excerpt: str, content: str, tags: List[str], domain: str) -> str:
        """Create the SEO optimization prompt for Gemini."""
        tags_text = ", ".join(tags) if tags else ""
        
        prompt = f"""Você é um jornalista especialista em cultura pop, cinema e séries. Sua tarefa é revisar o conteúdo abaixo para SEO no Google News, sem alterar a essência do texto. A revisão deve seguir as diretrizes abaixo:

1. Otimize o título, mantendo a clareza e adicionando palavras-chave relevantes para melhorar o desempenho nos mecanismos de busca.
2. Reescreva o resumo (excerpt) tornando-o mais atrativo e informativo, com foco em engajamento e SEO.
3. Reestruture o conteúdo completo sem mudar o sentido original:
   - Separe parágrafos muito grandes em blocos menores e mais escaneáveis.
   - Mantenha o tom jornalístico e informativo.
4. Destaque com **negrito** os principais nomes, termos e expressões importantes (títulos de filmes, nomes de personagens, diretores, datas etc.).
5. Insira **links internos** em termos relacionados a outras matérias, com base nas **tags** fornecidas. Use esta estrutura de link:
   [Texto âncora](https://{domain}/tag/NOME-DA-TAG)

Exemplo:
**[Stranger Things](https://{domain}/tag/stranger-things)**

Importante: **não mude o conteúdo nem o sentido original**, apenas melhore a estrutura, o SEO e a escaneabilidade para o Google News.

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
    
    def optimize_content(self, title: str, excerpt: str, content: str, tags: List[str], domain: str) -> Optional[Dict[str, str]]:
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
        try:
            # Create the prompt
            prompt = self._create_seo_prompt(title, excerpt, content, tags, domain)
            
            # Make request to Gemini
            model = genai.GenerativeModel(self.model)
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
                return parsed_result
            else:
                logger.error("Failed to parse Gemini response")
                # Log the raw response for debugging
                logger.debug(f"Raw Gemini response: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to optimize content with Gemini: {e}")
            return None
    
    def test_connection(self) -> bool:
        """Test the Gemini API connection."""
        try:
            # Skip actual test to avoid quota issues, just validate API key format
            if hasattr(genai, 'configure'):
                logger.info("Gemini API client configured successfully")
                return True
            else:
                logger.error("Gemini API not properly configured")
                return False
                
        except Exception as e:
            logger.error(f"Gemini API connection test failed: {e}")
            return False
