# Documentação Completa - WordPress SEO Optimizer

Sistema automatizado de otimização SEO para WordPress usando Google Gemini AI, TMDB e monitoramento em tempo real.

**Última atualização**: 30/07/2025 14:50

## Status do Sistema ✅

### Estado Atual
- **Sistema**: Operacional com melhorias implementadas
- **Chave Backup**: ✅ Configurada e funcional
- **Dashboard**: ✅ Ativo em tempo real
- **API TMDB**: ✅ Integrada com busca por categoria
- **Extração de Títulos**: ✅ Melhorada significativamente

### Melhorias Recentes (30/07/2025)
1. **Sistema de Backup de API Keys**: Alternância automática entre chaves quando quota esgota
2. **Busca por Categoria**: Sistema agora identifica se é filme (ID 24) ou série (ID 21)
3. **Extração de Títulos Melhorada**: Algoritmo mais preciso para identificar títulos reais
4. **Dashboard Corrigido**: Erro de JavaScript "redeclaration" resolvido

## Configurações e Credenciais

### WordPress
- **URL**: `https://www.maquinanerd.com.br/`
- **Usuário**: `Abel`
- **Senha App**: `Hl7M 5ZOE hMNQ M7A9 gFVy IEsB`
- **Domínio**: `[Configurado em WORDPRESS_DOMAIN]`
- **Author ID do João**: `6`

### Google Gemini API
- **Chave Principal**: `AIzaSyD7X2_8KPNZrnQnQ_643TjIJ2tpbkuRSms`
- **Chave Backup**: `AIzaSyDDkQ-htQ1WsNL-i6d_a9bwACl6cez8Cjs` ✅
- **Modelo**: `gemini-1.5-flash` (otimizado para quota)
- **Configurações**:
  - Temperature: 0.3
  - Max Output Tokens: 4000
  - Retry Logic: 5 tentativas com backoff exponencial
  - **Sistema de Backup**: Alternância automática entre chaves

### TMDB (The Movie Database)
- **API Key**: `cb60717161e33e2972bd217aabaa27f4`
- **Read Token**: `eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJjYjYwNzE3MTYxZTMzZTI5NzJiZDIxN2FhYmFhMjdmNCIsIm5iZiI6MTY4OTI2MjQ1NC4zODYsInN1YiI6IjY0YjAxOTc2NmEzNDQ4MDE0ZDM1NDYyNCIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.vw6ILzP4aEOLFL-MbIMiwPVvZGOmxMwRLtjo2TJLzns`
- **Base URL**: `https://api.themoviedb.org/3`
- **Imagens**: `https://image.tmdb.org/t/p`
- **Busca por Categoria**: 
  - ID 24 = Filmes → Search Movies
  - ID 21 = Séries → Search TV Shows

## Arquitetura do Sistema

### Módulos Principais

#### 1. main.py
- **Classe**: `SEOOptimizer`
- **Função**: Orquestrador principal do sistema
- **Recursos**:
  - Agendamento com `schedule` library
  - Controle de quota (2 posts por ciclo)
  - Process lock para evitar múltiplas instâncias
  - Integração com todas as APIs

#### 2. gemini_client.py
- **Classe**: `GeminiClient`
- **Função**: Interface com Google Gemini 1.5 Flash
- **Melhorias Recentes**:
  - **Sistema de Backup**: Suporte a múltiplas chaves API
  - **Alternância Automática**: Troca para backup quando quota esgota
  - **Gestão de Quota**: Controle rigoroso do limite diário
  - **Retry Logic**: 5 tentativas com backoff exponencial

#### 3. wordpress_client.py
- **Classe**: `WordPressClient`
- **Função**: Interface com WordPress REST API
- **Recursos**:
  - Busca de posts por autor e data
  - Atualização de posts (título, excerpt, conteúdo)
  - **Novo**: `get_post_categories()` para identificar tipo de conteúdo

#### 4. tmdb_client.py
- **Classe**: `TMDBClient`
- **Função**: Interface com TMDB API
- **Melhorias Recentes**:
  - **Busca por Categoria**: Prioriza movies/TV based na categoria do post
  - **Extração de Títulos Melhorada**: Algoritmo mais preciso
  - **Validação de Títulos**: Filtros para evitar termos irrelevantes
  - Suporte a imagens (poster/backdrop) e trailers do YouTube

#### 5. dashboard.py
- **Classe**: Flask app para monitoramento
- **Função**: Interface web em tempo real
- **Recursos**:
  - Status do sistema e APIs
  - Estatísticas de otimização
  - Logs em tempo real
  - **Corrigido**: Erro JavaScript de redeclaração

#### 6. config.py
- **Classe**: `Config`
- **Função**: Gerenciamento de configurações
- **Melhorias**:
  - **Suporte a Backup Keys**: Lista de chaves API disponíveis
  - Validação de URLs e credenciais

## Fluxo de Funcionamento

### 1. Inicialização
```
SEOOptimizer.initialize()
├── Testa conexão WordPress ✅
├── Testa conexão Gemini (principal + backup) ✅
└── Testa conexão TMDB ✅
```

### 2. Ciclo de Otimização (a cada 60 minutos)
```
run_optimization_cycle()
├── Verifica quota disponível
├── Busca posts novos do João (últimas 24h)
├── Limita a 2 posts por ciclo
└── Para cada post:
    ├── Identifica categorias (filme/série) 🆕
    ├── Extrai título principal do post 🆕
    ├── Busca mídia no TMDB por categoria 🆕
    ├── Otimiza com Gemini (com backup automático) 🆕
    └── Atualiza no WordPress
```

### 3. Sistema de Backup de API Keys 🆕
```
GeminiClient.optimize_content()
├── Tenta com chave principal
├── Se quota esgotada (429):
│   ├── Alterna para chave backup
│   ├── Retry imediato com nova chave
│   └── Log: "Switched to backup API key #2"
└── Se todas as chaves esgotadas:
    └── Aguarda retry com backoff exponencial
```

### 4. Busca TMDB Melhorada 🆕
```
find_media_for_post()
├── Identifica categoria do post
├── Extrai título principal (não frases aleatórias)
├── Busca prioritária:
│   ├── Categoria 24 (Filmes) → search_movie() primeiro
│   ├── Categoria 21 (Séries) → search_tv_show() primeiro
│   └── Sem categoria → busca ambos
└── Retorna: imagens, trailers, dados encontrados
```

## Prompt de Otimização SEO

O sistema usa um prompt especializado que:

1. **Otimiza para Google News**
2. **Mantém tom jornalístico**
3. **Adiciona negrito** em termos importantes
4. **Insere links internos** baseados nas tags
5. **Inclui mídia TMDB** (imagens e trailers) 🆕
6. **Estrutura em parágrafos curtos**

## Arquivos de Log e Dados

- **seo_optimizer.log**: Log principal do sistema
- **gemini_quota.json**: Controle de quota da API
- **seo_dashboard.db**: Banco SQLite para estatísticas
- **Process lock**: Previne execução simultânea

## Monitoramento e Dashboard

### URL: `http://127.0.0.1:5000` (ativo)

**Funcionalidades**:
- Status em tempo real das APIs
- Quota usage das chaves Gemini
- Estatísticas de posts otimizados
- Logs do sistema
- **Gráficos de performance** (corrigido)

## Comandos de Execução

### Execução Única (teste)
```bash
python main.py --once
```

### Execução Contínua (produção)
```bash
python main.py
```

### Dashboard
```bash
python dashboard.py
```

## Melhorias Implementadas (30/07/2025)

### 1. Sistema de Backup de Chaves API ✅
- Alternância automática quando quota principal esgota
- Suporte a múltiplas chaves de backup
- Log detalhado das trocas de chave

### 2. Busca por Categoria ✅
- Identifica categoria do post (24=Filmes, 21=Séries)
- Prioriza busca correta no TMDB
- Melhora significativa na precisão

### 3. Extração de Títulos Melhorada ✅
- Algoritmo específico para títulos de posts
- Filtra frases irrelevantes
- Patterns específicos para conteúdo de cultura pop

### 4. Correções de Dashboard ✅
- Erro JavaScript "redeclaration" corrigido
- Interface mais estável
- Atualização em tempo real funcionando

## Próximos Desenvolvimentos

1. **Analytics Avançados**: Métricas de SEO performance
2. **Otimização de Imagens**: Resize e otimização automática
3. **Integração com Google Analytics**: Tracking de resultados
4. **Sistema de Notificações**: Alertas por email/Slack

## Logs de Exemplo (Status Atual)

```
2025-07-30 14:49:03 - INFO - Found 10 new posts by João
2025-07-30 14:49:03 - INFO - Category analysis - Movies: True, TV: False
2025-07-30 14:49:03 - INFO - Extracted main title from post: 'King of the Hill'
2025-07-30 14:49:04 - INFO - Found movie: King of the Hill (1993)
2025-07-30 14:49:04 - WARNING - Quota exceeded on key #1
2025-07-30 14:49:04 - INFO - Switched to backup API key #2
2025-07-30 14:49:05 - INFO - Successfully optimized with backup key
```

---

**Sistema totalmente operacional com redundância e alta precisão na identificação de conteúdo!** 🚀