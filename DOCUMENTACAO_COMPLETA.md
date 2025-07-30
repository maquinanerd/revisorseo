
# WordPress SEO Optimizer - Documentação Completa

## Visão Geral do Sistema

O WordPress SEO Optimizer é um sistema automatizado em Python que monitora posts do WordPress de um autor específico (João) e os otimiza para SEO usando Inteligência Artificial do Google Gemini 1.5 Flash, com integração ao TMDB para obter imagens e trailers de filmes/séries.

## Funcionalidades Principais

### 1. Monitoramento Automático
- Monitora novos posts do autor João (ID: 6) nas últimas 24 horas
- Execução periódica a cada 60 minutos
- Controle de estado para evitar reprocessamento

### 2. Otimização de Conteúdo com IA
- **Título**: Otimização com palavras-chave relevantes
- **Resumo**: Reescrita para melhor engajamento e SEO
- **Conteúdo**: Reestruturação em parágrafos menores e escaneáveis
- **Formatação HTML**: Negrito em termos importantes, links internos
- **Integração de Mídia**: Inserção automática de imagens e trailers

### 3. Dashboard Web Interativo
- Interface web em Flask (porta 5000)
- Monitoramento em tempo real das otimizações
- Histórico de posts processados
- Métricas de desempenho e estatísticas
- Status dos sistemas conectados

### 4. Integração TMDB
- Busca automática de filmes e séries no conteúdo
- Download de posters e imagens de backdrop
- Integração de trailers do YouTube
- Suporte a múltiplos idiomas (português brasileiro)

## Configurações e Credenciais

### WordPress
- **URL**: `https://www.maquinanerd.com.br/`
- **Usuário**: `[Configurado em WORDPRESS_USERNAME]`
- **Senha App**: `[Configurado em WORDPRESS_PASSWORD]`
- **Domínio**: `[Configurado em WORDPRESS_DOMAIN]`
- **Author ID do João**: `6`

### Google Gemini API
- **Chave Principal**: `AIzaSyD7X2_8KPNZrnQnQ_643TjIJ2tpbkuRSms`
- **Chave Backup**: `AIzaSyDDkQ-htQ1WsNL-i6d_a9bwACl6cez8Cjs`
- **Modelo**: `gemini-1.5-flash` (otimizado para quota)
- **Configurações**:
  - Temperature: 0.3
  - Max Output Tokens: 4000
  - Retry Logic: 5 tentativas com backoff exponencial

### TMDB (The Movie Database)
- **API Key**: `cb60717161e33e2972bd217aabaa27f4`
- **Read Token**: `eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJjYjYwNzE3MTYxZTMzZTI5NzJiZDIxN2FhYmFhMjdmNCIsIm5iZiI6MTY4OTI2MjQ1NC4zODYsInN1YiI6IjY0YjAxOTc2NmEzNDQ4MDE0ZDM1NDYyNCIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.vw6ILzP4aEOLFL-MbIMiwPVvZGOmxMwRLtjo2TJLzns`
- **Base URL**: `https://api.themoviedb.org/3`
- **Imagens**: `https://image.tmdb.org/t/p`

## Arquitetura do Sistema

### Módulos Principais

#### 1. main.py
- **Classe**: `SEOOptimizer`
- **Função**: Orquestrador principal do sistema
- **Recursos**:
  - Agendamento com `schedule` library
  - Controle de quota (2 posts por ciclo)
  - Delay de 30 segundos entre posts
  - Logging completo

#### 2. wordpress_client.py
- **Classe**: `WordPressClient`
- **Função**: Interface com WordPress REST API
- **Recursos**:
  - Autenticação Basic Auth
  - Timeout de 60 segundos
  - Busca por autor e data
  - Atualização de posts

#### 3. gemini_client.py
- **Classe**: `GeminiClient`
- **Função**: Interface com Google Gemini API
- **Recursos**:
  - Prompts otimizados para SEO
  - Formatação HTML (não markdown)
  - Integração de dados de mídia
  - Tratamento de quota exceeded

#### 4. tmdb_client.py
- **Classe**: `TMDBClient`
- **Função**: Interface com TMDB API
- **Recursos**:
  - Busca de filmes e séries
  - Extração de títulos do conteúdo
  - Download de imagens (poster/backdrop)
  - Integração de trailers YouTube

#### 5. dashboard.py
- **Classe**: `SEODashboard`
- **Função**: Interface web de monitoramento
- **Recursos**:
  - Flask web server
  - Banco SQLite para histórico
  - APIs REST para dados
  - Interface responsiva

#### 6. config.py
- **Classe**: `Config`
- **Função**: Gerenciamento de configurações
- **Recursos**:
  - Carregamento de .env
  - Validação de variáveis obrigatórias
  - Suporte a chave backup

## Fluxo de Operação

### 1. Inicialização
```
Config → WordPress Client → Gemini Client → TMDB Client
```

### 2. Ciclo de Otimização
```
Buscar Posts Novos → Extrair Conteúdo → Buscar Mídia TMDB → 
Otimizar com Gemini → Atualizar WordPress → Log Resultado
```

### 3. Dashboard
```
Interface Web → Dados SQLite → APIs REST → Atualização Tempo Real
```

## Controles de Quota e Rate Limiting

### Gemini API
- **Limite**: 2 posts por ciclo
- **Delay**: 30 segundos entre posts
- **Retry**: 5 tentativas com backoff exponencial
- **Timeout**: Até 60 segundos de espera

### WordPress API
- **Timeout**: 60 segundos por requisição
- **Rate Limiting**: Controlado pelo servidor WordPress

### TMDB API
- **Timeout**: 10 segundos por requisição
- **Rate Limiting**: Padrão da API TMDB

## Banco de Dados (SQLite)

### Tabela: optimization_history
```sql
CREATE TABLE optimization_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    optimization_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    seo_score INTEGER,
    recommendations TEXT
);
```

### Tabela: seo_metrics
```sql
CREATE TABLE seo_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    total_posts INTEGER DEFAULT 0,
    optimized_posts INTEGER DEFAULT 0,
    failed_posts INTEGER DEFAULT 0,
    avg_seo_score REAL DEFAULT 0
);
```

## Logging e Monitoramento

### Arquivo de Log
- **Localização**: `seo_optimizer.log`
- **Formato**: `%(asctime)s - %(levelname)s - %(message)s`
- **Níveis**: INFO, WARNING, ERROR
- **Rotação**: Manual (não implementada)

### Métricas Monitoradas
- Posts processados por dia
- Taxa de sucesso/falha
- Tempo de processamento
- Erros de quota
- Status das conexões

## Prompt de Otimização SEO

O sistema usa um prompt especializado que instrui o Gemini a:

1. **Otimizar o título** mantendo clareza e adicionando palavras-chave
2. **Reescrever o resumo** para melhor engajamento
3. **Reestruturar o conteúdo** em parágrafos menores
4. **Aplicar formatação HTML**:
   - `<b>texto</b>` para negrito
   - `<a href="url">texto</a>` para links
5. **Inserir mídia**:
   - `<img>` para imagens com estilo responsivo
   - `<iframe>` para trailers YouTube
6. **Manter o tom jornalístico** e informativo

## Variáveis de Ambiente Necessárias

```env
# WordPress
WORDPRESS_URL=https://www.maquinanerd.com.br/
WORDPRESS_USERNAME=[seu_usuario]
WORDPRESS_PASSWORD=[sua_senha_app]
WORDPRESS_DOMAIN=https://www.maquinanerd.com.br

# Google Gemini
GEMINI_API_KEY=AIzaSyD7X2_8KPNZrnQnQ_643TjIJ2tpbkuRSms
GEMINI_API_KEY_BACKUP=AIzaSyDDkQ-htQ1WsNL-i6d_a9bwACl6cez8Cjs

# TMDB
TMDB_API_KEY=cb60717161e33e2972bd217aabaa27f4
TMDB_READ_TOKEN=eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJjYjYwNzE3MTYxZTMzZTI5NzJiZDIxN2FhYmFhMjdmNCIsIm5iZiI6MTY4OTI2MjQ1NC4zODYsInN1YiI6IjY0YjAxOTc2NmEzNDQ4MDE0ZDM1NDYyNCIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.vw6ILzP4aEOLFL-MbIMiwPVvZGOmxMwRLtjo2TJLzns
```

## Comandos de Execução

### Execução Única (Teste)
```bash
python main.py --once
```

### Execução Contínua (Produção)
```bash
python main.py
```

### Dashboard Web
```bash
python dashboard.py
```

## URLs de Acesso

### Dashboard Local
- **URL**: `http://0.0.0.0:5000`
- **Funcionalidades**:
  - Monitoramento em tempo real
  - Histórico de otimizações
  - Métricas de desempenho
  - Trigger manual de posts

### APIs Disponíveis
- `GET /api/dashboard-data` - Dados do dashboard
- `GET /api/pending-posts` - Posts pendentes
- `POST /api/optimize-post/<id>` - Otimizar post específico
- `GET /api/system-status` - Status dos sistemas

## Tratamento de Erros

### Quota Exceeded (429)
- Retry automático com backoff
- Log detalhado do erro
- Parada antecipada do ciclo

### Connection Errors
- Timeout configurável
- Retry com delay
- Fallback para próximo post

### Parsing Errors
- Validação de resposta Gemini
- Log de erro detalhado
- Continuação do processamento

## Segurança

### Autenticação WordPress
- Uso de Application Password (não senha principal)
- Basic Auth com base64 encoding
- Headers de User-Agent identificado

### Proteção de Chaves
- Variáveis de ambiente (não hardcoded)
- Suporte a chave backup
- Logs sem exposição de credenciais

## Performance

### Otimizações Implementadas
- Limite de 2 posts por ciclo
- Delay de 30 segundos entre posts
- Timeout de 60 segundos para WordPress
- Timeout de 10 segundos para TMDB
- Cache de posts processados

### Métricas de Performance
- Tempo médio por post: ~2-3 minutos
- Taxa de sucesso atual: Variável (quota dependent)
- Consumo de API: Controlado por limits

---

**Data de Criação**: 30 de Julho de 2025  
**Versão**: 2.0  
**Status**: Ativo com controle de quota  
**Próximas Melhorias**: Otimização de quota Gemini, cache de mídia TMDB
