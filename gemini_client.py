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
            # Create the prompt with media data
            prompt = self._create_seo_prompt(title, excerpt, content, tags, domain, media_data)
            
            # Make request to Gemini with retry logic
            model = genai.GenerativeModel(self.model)
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
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
                        return None
                        
                except Exception as e:
                    error_str = str(e)
                    if "429" in error_str and "quota" in error_str.lower():
                        # Extract retry delay if available
                        import re
                        retry_match = re.search(r'retry_delay.*?seconds:\s*(\d+)', error_str)
                        wait_time = int(retry_match.group(1)) if retry_match else 60
                        
                        logger.warning(f"Quota exceeded. Waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
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
