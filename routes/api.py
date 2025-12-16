"""
BigSearch API Routes
====================
REST API endpoints for the BigSearch search engine.
"""

from flask import Blueprint, request, jsonify, current_app
import config

# Create blueprint
api = Blueprint('api', __name__, url_prefix='/api')



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
        return jsonify({
            "error": str(e),
            "success": False
        }), 500


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
        return jsonify({
            "error": str(e),
            "success": False
        }), 500


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
        return jsonify({
            "error": str(e),
            "success": False
        }), 500


# ==================== INDEXING ENDPOINTS ====================

@api.route('/index/html', methods=['POST'])
def index_html():
    """
    Index HTML endpoint - indexes a web page from a URL.
    
    Request Body (JSON):
        - url (str): URL of the HTML page to index (required)
    
    Returns:
        JSON with indexing status and assigned document ID
    
    Note: This is a placeholder endpoint. Implementation pending.
    """
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
        
        # TODO: Implement HTML indexing logic
        # 1. Fetch HTML from URL
        # 2. Parse and extract text
        # 3. Generate forward index entry
        # 4. Update inverted index/barrels
        # 5. Update embeddings (optional)
        
        engine = current_app.config['search_engine']
        next_id = engine.state.get("last_html_id", 0) + 1
        
        return jsonify({
            "success": True,
            "message": "HTML indexing not yet implemented",
            "url": url,
            "assigned_id": f"H{next_id}",
            "status": "pending"
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "success": False
        }), 500


@api.route('/index/json', methods=['POST'])
def index_json():
    """
    Index JSON endpoint - indexes a JSON document.
    
    Request Body:
        - Can be a JSON object directly (Content-Type: application/json)
        - Or multipart form with 'file' field containing JSON file
    
    Returns:
        JSON with indexing status and assigned document ID
    
    Note: This is a placeholder endpoint. Implementation pending.
    """
    try:
        # Check if file upload or JSON body
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return jsonify({
                    "error": "No file selected",
                    "success": False
                }), 400
            
            if not file.filename.endswith('.json'):
                return jsonify({
                    "error": "File must be a JSON file",
                    "success": False
                }), 400
            
            # Read file content
            content = file.read().decode('utf-8')
            import json
            document = json.loads(content)
            source = "file"
        else:
            # JSON in request body
            document = request.get_json()
            if not document:
                return jsonify({
                    "error": "No JSON data provided",
                    "success": False
                }), 400
            source = "body"
        
        # TODO: Implement JSON indexing logic
        # 1. Validate JSON structure
        # 2. Extract text content
        # 3. Generate forward index entry
        # 4. Update inverted index/barrels
        # 5. Update embeddings (optional)
        
        engine = current_app.config['search_engine']
        next_id = engine.state.get("last_json_id", 0) + 1
        
        return jsonify({
            "success": True,
            "message": "JSON indexing not yet implemented",
            "source": source,
            "assigned_id": f"J{next_id}",
            "status": "pending"
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "success": False
        }), 500


@api.route('/index/pdf', methods=['POST'])
def index_pdf():
    """
    Index PDF endpoint - indexes a PDF document.
    
    Request Body:
        - Multipart form with 'file' field containing PDF file (required)
    
    Returns:
        JSON with indexing status and assigned document ID
    
    Note: This is a placeholder endpoint. Implementation pending.
    """
    try:
        if 'file' not in request.files:
            return jsonify({
                "error": "No file provided. Use 'file' field in multipart form.",
                "success": False
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                "error": "No file selected",
                "success": False
            }), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({
                "error": "File must be a PDF",
                "success": False
            }), 400
        
        # TODO: Implement PDF indexing logic
        # 1. Save PDF temporarily
        # 2. Extract text using PDF parser (PyPDF2, pdfminer, etc.)
        # 3. Generate forward index entry
        # 4. Update inverted index/barrels
        # 5. Update embeddings (optional)
        # 6. Clean up temporary file
        
        engine = current_app.config['search_engine']
        next_id = engine.state.get("last_pdf_id", 0) + 1
        
        return jsonify({
            "success": True,
            "message": "PDF indexing not yet implemented",
            "filename": file.filename,
            "assigned_id": f"P{next_id}",
            "status": "pending"
        })
        
    except Exception as e:
        return jsonify({
            "error": str(e),
            "success": False
        }), 500


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
        return jsonify({
            "success": False,
            "status": "error",
            "error": str(e)
        }), 500


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
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 503
