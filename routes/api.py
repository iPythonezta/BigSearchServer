"""
BigSearch API Routes
====================
REST API endpoints for the BigSearch search engine.
"""

from flask import Blueprint, request, jsonify, current_app
import requests
import config
import traceback
import sys

# Create blueprint
api = Blueprint('api', __name__, url_prefix='/api')


def handle_error(e, endpoint_name):
    """
    Print detailed error traceback and return JSON error response.
    
    Args:
        e: The exception object
        endpoint_name: Name of the endpoint where error occurred
    
    Returns:
        Tuple of (json_response, status_code)
    """
    print("\n" + "=" * 70, file=sys.stderr)
    print(f"ERROR in {endpoint_name}", file=sys.stderr)
    print("=" * 70, file=sys.stderr)
    traceback.print_exc()
    print("=" * 70 + "\n", file=sys.stderr)
    
    return jsonify({
        "error": str(e),
        "success": False,
        "traceback": traceback.format_exc()  # Include traceback in response for debugging
    }), 500



# ==================== SEARCH ENDPOINTS ====================

@api.route('/search', methods=['POST'])
def search():
    """
    Search endpoint - performs hybrid search on the corpus.
    
    Request Body (JSON):
        - query (str): Search query string (required)
        - use_semantic (bool): Whether to use semantic search (default: True)
        - semantic_weight (int): Weight for semantic scores (default: 20)
    
    Returns:
        JSON array of search results sorted by score
    """
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({
                "error": "Missing required field: query",
                "success": False
            }), 400
        
        query = data['query'].strip()
        
        if not query:
            return jsonify({
                "error": "Query cannot be empty",
                "success": False
            }), 400
        
        use_semantic = data.get('use_semantic', config.DEFAULT_USE_SEMANTIC)
        semantic_weight = data.get('semantic_weight', config.DEFAULT_SEMANTIC_WEIGHT)
        
        engine = current_app.config['search_engine']
        results = engine.search(
            query=query,
            use_semantic=use_semantic,
            semantic_weight=semantic_weight
        )
        
        return jsonify({
            "success": True,
            "query": query,
            "total_results": len(results),
            "results": results
        })
        
    except Exception as e:
        return handle_error(e, "/api/search (POST)")


@api.route('/search', methods=['GET'])
def search_get():
    """
    Search endpoint (GET) - performs hybrid search on the corpus.
    
    Query Parameters:
        - q (str): Search query string (required)
        - use_semantic (bool): Whether to use semantic search (default: True)
        - semantic_weight (int): Weight for semantic scores (default: 20)
    
    Returns:
        JSON array of search results sorted by score
    """
    try:
        query = request.args.get('q', '').strip()
        
        if not query:
            return jsonify({
                "error": "Missing required parameter: q",
                "success": False
            }), 400
        
        use_semantic = request.args.get('use_semantic', 'true').lower() == 'true'
        semantic_weight = int(request.args.get('semantic_weight', config.DEFAULT_SEMANTIC_WEIGHT))
        
        engine = current_app.config['search_engine']
        results = engine.search(
            query=query,
            use_semantic=use_semantic,
            semantic_weight=semantic_weight
        )
        
        return jsonify({
            "success": True,
            "query": query,
            "total_results": len(results),
            "results": results
        })
        
    except Exception as e:
        return handle_error(e, "/api/search (GET)")


# ==================== AUTOCOMPLETE ENDPOINTS ====================

@api.route('/autocomplete', methods=['GET'])
def autocomplete():
    """
    Autocomplete endpoint - returns query suggestions based on prefix.
    
    Query Parameters:
        - q (str): Partial word/query for autocomplete (required)
        - limit (int): Maximum number of suggestions (default: 5)
    
    Returns:
        JSON array of autocomplete suggestions sorted by term frequency
    """
    try:
        query = request.args.get('q', '').strip()
        limit = int(request.args.get('limit', 5))
        
        if not query:
            return jsonify({
                "error": "Missing required parameter: q",
                "success": False
            }), 400
        
        # Get trie from app context
        trie = current_app.config.get('autocomplete_trie')
        
        if not trie or not trie.loaded:
            return jsonify({
                "success": True,
                "query": query,
                "suggestions": [],
                "message": "Autocomplete service not available"
            })
        
        # Get suggestions
        suggestions = trie.suggest(query, k=limit)
        
        return jsonify({
            "success": True,
            "query": query,
            "suggestions": suggestions,
            "count": len(suggestions)
        })
        
    except Exception as e:
        return handle_error(e, "/api/autocomplete (GET)")


# ==================== INDEXING ENDPOINTS ====================

@api.route('/index/html', methods=['POST'])
def index_html():
    """
    Index HTML endpoint - indexes a web page from a URL.
    
    Request Body (JSON):
        - url (str): URL of the HTML page to index (required)
    
    Returns:
        JSON with indexing status and assigned document ID
    
    Example Response:
        {
            "success": true,
            "doc_id": "H100001",
            "title": "Page Title",
            "url": "https://example.com/page.html",
            "indexed_at": "2024-01-15T10:30:00.000000Z"
        }
    """
    import requests
    from datetime import datetime
    
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({
                "error": "Missing required field: url",
                "success": False
            }), 400
        
        url = data['url'].strip()
        
        if not url:
            return jsonify({
                "error": "URL cannot be empty",
                "success": False
            }), 400
        
        engine = current_app.config['search_engine']
        
        # Fetch HTML content from URL (no crawling beyond this URL)
        html_content = requests.get(url, headers={
            'User-Agent': 'Chrome/91.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }, timeout=30)

        if html_content.status_code >= 300:
            return jsonify({
                "error": f"Failed to fetch URL: HTTP {html_content.status_code}",
                "success": False
            }), 400

        text = html_content.content
        doc_id = engine.index_new_html(text, url)
        
        # Extract title from HTML if available
        title = ""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(text, 'lxml')
            if soup.title:
                title = soup.title.text.strip()
        except Exception:
            pass
        
        return jsonify({
            "success": True,
            "doc_id": doc_id,
            "title": title,
            "url": url if url else None,
            "indexed_at": datetime.utcnow().isoformat() + "Z"
        }), 200
        
    except Exception as e:
        return handle_error(e, "/api/index/html (POST)")


@api.route('/index/rps', methods=['POST'])
@api.route('/index/pdf', methods=['POST'])  # Alias for PDF indexing
def index_rps():
    """
    Index RPS endpoint - indexes research papers from PDF files only.
    
    Request Body (multipart/form-data only):
        - file: PDF file (.pdf) - required
        - url: Optional string (metadata only, no fetching/crawling)
    
    Returns:
        JSON with indexing status and assigned document ID
    
    Example Response:
        {
            "success": true,
            "doc_id": "P200001",
            "title": "Paper Title",
            "url": "https://example.com/paper.pdf",
            "indexed_at": "2024-01-15T10:30:00.000000Z"
        }
    """
    import orjson
    from datetime import datetime
    from FileHandler.file_handler import FileHandler
    
    try:
        engine = current_app.config['search_engine']
        
        # Reject JSON body requests
        if request.content_type and 'application/json' in request.content_type:
            return jsonify({
                "error": "JSON body not accepted. Use multipart/form-data with 'file' (PDF).",
                "success": False
            }), 400
        
        # Must use multipart/form-data with file field
        if 'file' not in request.files:
            return jsonify({
                "error": "No file provided. Use multipart/form-data with 'file' field containing a PDF.",
                "success": False
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                "error": "No file selected",
                "success": False
            }), 400
        
        filename_lower = file.filename.lower()
        
        # Reject JSON files
        if filename_lower.endswith('.json'):
            return jsonify({
                "error": "JSON files are not accepted. Please upload a PDF file.",
                "success": False
            }), 400
        
        # Only accept PDF files
        if not filename_lower.endswith('.pdf'):
            return jsonify({
                "error": "File must be a PDF (.pdf) file",
                "success": False
            }), 400
        
        # Get optional URL (metadata only)
        url = request.form.get('url', '').strip()
        
        # Read PDF file
        file_bytes = file.read()
        
        if not file_bytes:
            return jsonify({
                "error": "PDF file is empty",
                "success": False
            }), 400
        
        # Convert PDF to CORD-19 JSON format using FileHandler
        try:
            document = FileHandler.pdf_to_json(file_bytes, file.filename)
        except Exception as e:
            return jsonify({
                "error": f"Failed to process PDF: {str(e)}",
                "success": False
            }), 400
        
        # Validate document structure
        if not isinstance(document, dict) or 'metadata' not in document:
            return jsonify({
                "error": "Failed to extract document structure from PDF",
                "success": False
            }), 400
        
        # Extract title
        title = document.get('metadata', {}).get('title', '')
        
        # Convert to binary JSON
        file_content = orjson.dumps(document)
        
        # Call the indexing function (url is metadata only, no fetching)
        doc_id = engine.index_new_rps(file_content, url)
        
        return jsonify({
            "success": True,
            "doc_id": doc_id,
            "title": title,
            "url": url if url else None,
            "indexed_at": datetime.utcnow().isoformat() + "Z"
        }), 200
        
    except Exception as e:
        return handle_error(e, "/api/index/rps (POST)")


@api.route('/index/json', methods=['POST'])
def index_json():
    """
    Index JSON endpoint - indexes research papers from JSON files or JSON body.
    
    Request Body Options:
        1. Multipart form (multipart/form-data):
           - file: JSON file (.json) - required if JSON body not provided
           - url: Optional string (metadata only, no fetching/crawling)
        
        2. JSON body (application/json):
           - document: JSON document object (CORD-19 format)
           - url: Optional string (metadata only, no fetching/crawling)
           OR directly:
           - metadata, abstract, body_text, etc. (CORD-19 format)
           - url: Optional string (metadata only)
    
    Returns:
        JSON with indexing status and assigned document ID
    
    Example Response:
        {
            "success": true,
            "doc_id": "P200001",
            "title": "Paper Title",
            "url": "https://example.com/paper.json",
            "indexed_at": "2024-01-15T10:30:00.000000Z"
        }
    """
    import orjson
    from datetime import datetime
    
    try:
        engine = current_app.config['search_engine']
        url = ""
        file_content = None
        title = ""
        
        # Check if file upload or JSON body
        if 'file' in request.files:
            # Multipart form upload
            file = request.files['file']
            if file.filename == '':
                return jsonify({
                    "error": "No file selected",
                    "success": False
                }), 400
            
            filename_lower = file.filename.lower()
            
            # Only accept JSON files
            if not filename_lower.endswith('.json'):
                return jsonify({
                    "error": "File must be a JSON (.json) file",
                    "success": False
                }), 400
            
            # Read file as binary (as required by index_new_rps)
            file_content = file.read()
            
            if not file_content:
                return jsonify({
                    "error": "JSON file is empty",
                    "success": False
                }), 400
            
            # Get optional URL from form (metadata only)
            url = request.form.get('url', '').strip()
            
            # Validate JSON can be parsed
            try:
                parsed = orjson.loads(file_content)
                if not isinstance(parsed, dict):
                    return jsonify({
                        "error": "Invalid JSON structure: document must be a JSON object",
                        "success": False
                    }), 400
                # Try to extract title
                title = parsed.get('metadata', {}).get('title', '')
            except orjson.JSONDecodeError as e:
                return jsonify({
                    "error": f"Invalid JSON format: {str(e)}",
                    "success": False
                }), 400
            
        else:
            # JSON in request body
            data = request.get_json()
            if not data:
                return jsonify({
                    "error": "No JSON data provided. Use multipart/form-data with 'file' or provide JSON in request body.",
                    "success": False
                }), 400
            
            # Handle nested "document" key or direct JSON
            document = data.get('document', data)
            url = data.get('url', '').strip()  # Optional, metadata only
            
            # Validate JSON structure (basic check)
            if not isinstance(document, dict):
                return jsonify({
                    "error": "Invalid JSON structure: document must be a JSON object",
                    "success": False
                }), 400
            
            # Try to extract title for response
            try:
                title = document.get('metadata', {}).get('title', '')
            except (KeyError, AttributeError):
                pass
            
            # Convert JSON object to binary bytes (as required by index_new_rps)
            file_content = orjson.dumps(document)
        
        # Validate that we have content
        if not file_content:
            return jsonify({
                "error": "No document content provided",
                "success": False
            }), 400
        
        # Call the indexing function (url is metadata only, no fetching)
        doc_id = engine.index_new_rps(file_content, url)
        
        # Extract title if not already extracted
        if not title:
            try:
                parsed = orjson.loads(file_content)
                title = parsed.get('metadata', {}).get('title', '')
            except (KeyError, AttributeError, orjson.JSONDecodeError):
                title = ""
        
        return jsonify({
            "success": True,
            "doc_id": doc_id,
            "title": title,
            "url": url if url else None,
            "indexed_at": datetime.utcnow().isoformat() + "Z"
        }), 200
        
    except Exception as e:
        return handle_error(e, "/api/index/json (POST)")




# ==================== STATUS ENDPOINTS ====================

@api.route('/status', methods=['GET'])
def status():
    """
    Status endpoint - returns current engine status and statistics.
    
    Returns:
        JSON with engine state information
    """
    try:
        engine = current_app.config['search_engine']
        state = engine.get_state()
        
        return jsonify({
            "success": True,
            "status": "running",
            "engine": state
        })
        
    except Exception as e:
        return handle_error(e, "/api/status (GET)")


@api.route('/health', methods=['GET'])
def health():
    """
    Health check endpoint for load balancers and monitoring.
    
    Returns:
        JSON with health status
    """
    try:
        engine = current_app.config['search_engine']
        
        return jsonify({
            "status": "healthy",
            "initialized": engine.initialized,
            "semantic_available": engine.semantic_available
        })
        
    except Exception as e:
        return handle_error(e, "/api/health (GET)")


# ==================== PERSISTENCE ENDPOINTS ====================

@api.route('/save', methods=['POST'])
def save_all():
    """
    Manual save endpoint - triggers a full save of all engine data.
    
    This will:
    - Save all embeddings to disk
    - Flush all pending barrel updates
    - Save URL and title mappings
    - Save research paper info
    - Save engine state
    
    Returns:
        JSON with save status
    """
    try:
        engine = current_app.config['search_engine']
        
        print("\nManual save triggered via API...")
        engine.save_all_files()
        engine.save_state()
        engine.save_word_cache()
        
        return jsonify({
            "success": True,
            "message": "All data saved successfully",
            "state": engine.get_state()
        })
        
    except Exception as e:
        return handle_error(e, "/api/save (POST)")
