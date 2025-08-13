# News RAG App V2

A sophisticated **Retrieval-Augmented Generation (RAG)** application that scrapes, processes, and serves hip-hop news articles with intelligent conversational AI capabilities.

## 🚀 Features

- **Multi-Source News Scraping**: Automated daily scraping from 8 major hip-hop news sources
- **Dual Storage Architecture**: 
  - Neo4j graph database for structured queries
  - Pinecone vector database for semantic search
- **Intelligent RAG Pipeline**: Context-aware responses using Google's Gemini 2.0 Flash Lite
- **Session Management**: Multi-session conversation memory with context preservation
- **RESTful API**: Clean FastAPI endpoints for all operations
- **Docker Support**: Containerized deployment with all dependencies

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   News Sources  │───▶│   Web Scrapers  │───▶│  Data Pipeline  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │◀───│   RAG Service   │◀───│  Dual Storage   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                               ┌───────┴───────┐
                                               │               │
                                               ▼               ▼
                                        ┌─────────────┐ ┌─────────────┐
                                        │   Neo4j     │ │  Pinecone   │
                                        │ (Graph DB)  │ │ (Vector DB) │
                                        └─────────────┘ └─────────────┘
```

## 📊 Supported News Sources

- **AllHipHop.com**
- **HipHopDX.com**
- **OkayPlayer.com**
- **RapRadar.com**
- **HotNewHipHop.com**
- **HipHop Since1987.com**
- **HipHopHero.com**
- **RapUp.com**

## 🛠️ Tech Stack

- **Backend**: FastAPI, Python 3.12
- **AI/ML**: LangChain, Google Gemini 2.0 Flash Lite
- **Databases**: Neo4j (Graph), Pinecone (Vector)
- **Web Scraping**: BeautifulSoup4, Selenium, Playwright
- **Containerization**: Docker
- **Environment**: Python-dotenv

## 📋 Prerequisites

- Docker and Docker Compose
- Python 3.12+ (for local development)
- Neo4j Database
- Pinecone Account
- Google AI API Key

## ⚙️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/prakher01/New_News_Rag_App_V2.git
cd New_News_Rag_App_V2
```

### 2. Environment Configuration

Create a `.env` file in the project root:

```env
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=neo4j

# Pinecone Configuration
PINECONE_API_KEY=your_pinecone_api_key
PINECONE_ENV=your_pinecone_environment
PINECONE_INDEX_NAME=news-data-index

# Google AI Configuration
GOOGLE_API_KEY=your_google_api_key
```

### 3. Docker Deployment (Recommended)

```bash
# Build the Docker image
docker build -t news-rag-app .

# Run the container
docker run -p 8080:8080 --env-file .env news-rag-app
```

### 4. Local Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install

# Run the application
uvicorn main:app --host 0.0.0.0 --port 8080
```

## 🔧 API Endpoints

### Core Operations

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/ask` | Ask questions with conversation memory |
| `GET` | `/run-pipeline` | Execute daily news scraping pipeline |
| `GET` | `/latest-articles` | Get latest articles with URLs |
| `GET` | `/health` | Health check endpoint |

### Session Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/session/new` | Create new conversation session |
| `POST` | `/session/clear` | Clear session history |
| `POST` | `/session/delete` | Delete session |
| `GET` | `/session/{session_id}/history` | Get conversation history |

### Example Usage

```bash
# Ask a question
curl -X POST "http://localhost:8080/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the latest hip-hop news?",
    "session_id": "optional-session-id"
  }'

# Run the scraping pipeline
curl -X GET "http://localhost:8080/run-pipeline"

# Get latest articles
curl -X GET "http://localhost:8080/latest-articles"
```

## 🔄 Data Pipeline

The application follows a comprehensive data processing pipeline:

1. **Scraping**: Daily automated scraping from configured news sources
2. **Processing**: Data cleaning, date parsing, and content extraction
3. **Storage**: 
   - Structured data stored in Neo4j with relationships
   - Text embeddings stored in Pinecone for semantic search
4. **Retrieval**: Intelligent query routing between graph and vector databases
5. **Generation**: Context-aware responses using Google's Gemini model

## 🗂️ Project Structure

```
New_News_Rag_App_V2/
├── api/                          # FastAPI routes and endpoints
├── daily_news_pipeline/          # News scraping and processing
│   ├── news_scrapers/           # Individual site scrapers
│   └── data_uploder/            # Data upload utilities
├── data/                        # Database connections
├── llm/                         # LLM setup and prompts
├── services/                    # Business logic services
├── pipelines/                   # Data processing pipelines
├── utils/                       # Utility functions
├── log/                         # Application logs
├── main.py                      # FastAPI application entry point
├── configuration.py             # Configuration management
├── requirements.txt             # Python dependencies
└── DockerFile                   # Container configuration
```

## 🧪 Testing

```bash
# Test the health endpoint
curl http://localhost:8080/health

# Test with a simple query
curl -X POST "http://localhost:8080/ask" \
  -H "Content-Type: application/json" \
  -d '{"query": "Hello, what can you tell me about recent hip-hop news?"}'
```

## 📝 Configuration

The application uses environment variables for configuration. Key settings include:

- **Database connections**: Neo4j and Pinecone credentials
- **API keys**: Google AI API for LLM operations
- **Logging**: Configurable logging levels and file locations
- **Pipeline settings**: Scraping intervals and data processing parameters

## 🚨 Troubleshooting

### Common Issues

1. **Docker Build Fails**:
   ```bash
   # Ensure all dependencies are available
   docker system prune -a
   docker build --no-cache -t news-rag-app .
   ```

2. **Database Connection Issues**:
   - Verify Neo4j is running and accessible
   - Check Pinecone API key and environment settings
   - Ensure firewall rules allow connections

3. **Scraping Issues**:
   - Check internet connectivity
   - Verify target websites are accessible
   - Review scraper logs in `log/` directory

### Logs

Application logs are stored in the `log/` directory:
- `scraper.log`: Web scraping operations
- `uploader.log`: Data upload operations


