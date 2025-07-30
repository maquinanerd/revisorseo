# WordPress SEO Optimizer

## Overview

This is a Python-based automation system that monitors WordPress posts from a specific author ("João") and optimizes them for SEO using Google Gemini 1.5 Pro. The system automatically processes new posts, enhances their content structure, adds internal links, and updates the original posts with optimized versions designed for Google News performance.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

The application follows a modular architecture with four main components:

1. **Configuration Management** (`config.py`) - Centralized environment variable handling
2. **WordPress Integration** (`wordpress_client.py`) - REST API client for WordPress operations
3. **AI Content Optimization** (`gemini_client.py`) - Google Gemini API client for content enhancement
4. **Orchestration** (`main.py`) - Main scheduler and workflow coordinator

The system is designed as a scheduled automation tool that runs periodically to check for new posts and process them automatically.

## Key Components

### Configuration Management
- **Purpose**: Manage all environment variables and validate required settings
- **Technology**: Python with python-dotenv for environment variable loading
- **Key Features**: Validation of required credentials, centralized config access

### WordPress Client
- **Purpose**: Interface with WordPress REST API for reading and updating posts
- **Authentication**: Basic Auth using application passwords
- **Operations**: Retrieve posts by author, update post content, manage tags and metadata
- **Error Handling**: Request timeout and HTTP error management

### Gemini AI Client
- **Purpose**: Optimize content using Google Gemini 1.5 Pro for SEO enhancement
- **Features**: 
  - Content restructuring for better readability
  - Internal link insertion based on post tags
  - SEO optimization for Google News
  - Bold formatting for important terms

### Main Orchestrator
- **Purpose**: Coordinate the entire workflow and manage scheduling
- **Features**:
  - Periodic execution using the `schedule` library
  - Author identification and filtering
  - Post processing state management
  - Comprehensive logging

## Data Flow

1. **Initialization**: Load configuration and establish connections to WordPress and Gemini APIs
2. **Author Discovery**: Find João's author ID in WordPress
3. **Post Monitoring**: Periodically check for new posts by the target author
4. **Content Processing**: 
   - Extract post data (title, excerpt, content, tags)
   - Send to Gemini for SEO optimization
   - Parse optimized response
5. **Content Update**: Update the original WordPress post with optimized content
6. **State Tracking**: Maintain record of processed posts to avoid duplication

## External Dependencies

### Required Services
- **WordPress Site**: Target WordPress installation with REST API enabled
- **Google Gemini API**: Access to Gemini 1.5 Pro model for content optimization

### Python Libraries
- `requests`: HTTP client for WordPress API communication
- `google-genai`: Official Google Gemini API client
- `schedule`: Task scheduling for periodic execution
- `python-dotenv`: Environment variable management
- `logging`: Built-in logging for monitoring and debugging

### Environment Variables
- `WORDPRESS_URL`: WordPress site URL
- `WORDPRESS_USERNAME`: WordPress username for API access
- `WORDPRESS_PASSWORD`: WordPress application password
- `WORDPRESS_DOMAIN`: Domain for internal link generation
- `GEMINI_API_KEY`: Google Gemini API key

## Deployment Strategy

### Local Development
- Environment variables loaded from `.env` file
- Manual execution or development scheduling
- File-based logging for debugging

### Production Deployment
- Environment variables configured in hosting environment
- Automated scheduling (cron job or container scheduler)
- Centralized logging and monitoring

### Key Considerations
- **Authentication Security**: Uses WordPress application passwords instead of main credentials
- **Rate Limiting**: Implements request timeouts and error handling for API calls
- **State Management**: Tracks processed posts to prevent duplicate processing
- **Error Recovery**: Comprehensive logging and exception handling for unattended operation

### Monitoring
- File-based logging (`seo_optimizer.log`)
- Console output for real-time monitoring
- Structured logging with timestamps and severity levels

The system is designed to run as a background service, automatically processing new content from the specified author while maintaining detailed logs of all operations.