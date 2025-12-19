# BigSearch Server

A Flask-based REST API server for the BigSearch search engine. This server provides endpoints for hybrid search (keyword + semantic), autocomplete suggestions, and document indexing.

Already Deployed at: https://bigsearch.azurewebsites.net/

## Features

- **Hybrid Search**: Combines keyword-based search with semantic similarity
- **Word-Level Caching**: LRU cache with persistence for fast repeated queries
- **PageRank & DomainRank**: Results ranked using pre-computed authority scores
- **Phrase Matching**: Bonus scoring for consecutive word matches
- **State Tracking**: Maintains document IDs for dynamic indexing

## Project Structure

```
BigSearchServer/
├── app.py                 # Main Flask application entry point
├── config.py              # Server configuration
├── requirements.txt       # Python dependencies
├── engine/
│   ├── __init__.py
│   └── search_engine.py   # Core search engine implementation
├── routes/
│   ├── __init__.py
│   └── api.py             # API endpoint definitions
├── data/
│   ├── barrels/           # Inverted index barrels (.msgpack)
│   ├── semantic/          # Embeddings and TF-IDF data
│   ├── rankings/          # PageRank, DomainRank, CitationRank CSVs
│   ├── mappings/          # URL/ID mapping files
│   └── models/            # Word2Vec model
└── cache/                 # Word cache persistence
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Copy Data Files

Copy the following files from the main BigSearch project to the respective directories:

#### Barrels (data/barrels/)
```bash
# Copy all .msgpack files and barrels_index.json from BigSearch/Barrels/
cp ../Barrels/*.msgpack data/barrels/
cp ../Barrels/barrels_index.json data/barrels/
```

#### Semantic Data (data/semantic/)
```bash
# Copy from BigSearch/Semantic Search Data/
cp "../Semantic Search Data/html_embeddings.json" data/semantic/
cp "../Semantic Search Data/json_embeddings.json" data/semantic/
cp "../Semantic Search Data/idf_map.json" data/semantic/
```

#### Ranking Data (data/rankings/)
```bash
# Copy from BigSearch/Page Rank Results/
cp "../Page Rank Results/page_rank_results_with_urls.csv" data/rankings/
cp "../Page Rank Results/domain_rank_results_with_domain_nm.csv" data/rankings/
cp "../Page Rank Results/citation_ranks_with_scores.csv" data/rankings/
```

#### Mappings (data/mappings/)
```bash
# Copy from BigSearch/Data/
cp ../Data/ind_to_url.json data/mappings/

# Copy metadata from BigSearch/Data/Cord 19/
cp "../Data/Cord 19/metadata_cleaned.csv" data/mappings/
```

#### Word2Vec Model (data/models/)
```bash
# Copy from your word2vec training output
cp path/to/fine_tunned_model.word2vec.txt data/models/
```

### 3. Run the Server

## Frontend Integration

If you are working with the full-stack version of the project, follow these steps to build the frontend and serve it through the Flask backend.

### 1. Build the Frontend
Navigate to the frontend directory, install dependencies, and generate the production build:
```bash
cd frontend
npm install
npm run build
```

Sync the build to backend:

```bash

cd ..  # Return to repo root (where sync_frontend_build.py is)
python sync_frontend_build.py
```
4. Run the Server

Start the server using main.py:

```bash

python main.py
```
The server will start on http://localhost:5000.

The frontend index.html should load automatically.

API calls to /api/* will work in the background.

## API Endpoints

### Search

**GET** `/api/search?q=<query>`

Search for documents matching the query.

**Parameters:**
- `q` (required): Search query string

**Response:**
```json
{
    "query": "machine learning",
    "total_results": 150,
    "results": [
        {
            "doc_id": "12345",
            "title": "Introduction to Machine Learning",
            "url": "https://example.com/ml-intro",
            "score": 0.95,
            "type": "html"
        },
        ...
    ]
}
```

### Autocomplete

**GET** `/api/autocomplete?q=<prefix>`

Get autocomplete suggestions for a prefix.

**Parameters:**
- `q` (required): Prefix to autocomplete

**Response:**
```json
{
    "prefix": "mach",
    "suggestions": ["machine", "machine learning", "machinery"]
}
```

### Index Documents

**POST** `/api/index/html`

Index a new HTML document from a URL.

**Body:**
```json
{
    "url": "https://example.com/new-page"
}
```

**POST** `/api/index/json`

Index a new JSON document.

**Body:** JSON object or file upload

**POST** `/api/index/pdf`

Index a PDF document.

**Body:** PDF file upload (multipart/form-data)

### Status

**GET** `/api/status`

Get current engine state including document counts and cache statistics.

**Response:**
```json
{
    "last_html_id": 5000,
    "last_json_id": 200000,
    "last_pdf_id": 50,
    "cache_size": 350,
    "cache_max_size": 500
}
```

### Health Check

**GET** `/health`

Simple health check endpoint.

**Response:**
```json
{
    "status": "healthy",
    "service": "BigSearch API"
}
```

## Configuration

Edit `config.py` to customize:

- `PORT`: Server port (default: 5000)
- `DEBUG`: Debug mode (default: True)
- `CACHE_MAX_SIZE`: Maximum words in cache (default: 500)
- `CACHE_SAVE_FREQUENCY`: Save cache after N updates (default: 50)
- Data directory paths

## Development

### Adding New Endpoints

1. Add route to `routes/api.py`
2. Implement logic in `engine/search_engine.py` if needed
3. Update this README

### Extending Search Logic

The `SearchEngine` class in `engine/search_engine.py` contains:
- `search()`: Main search entry point
- `score_html_files()`: HTML document scoring
- `rank_research_papers()`: Research paper scoring
- `get_semantic_scores()`: Vectorized semantic similarity

## License

Part of the BigSearch project.
