"""
BigSearch Server - Main Application Entry Point

A Flask-based REST API server for the BigSearch search engine.
Provides endpoints for searching, autocomplete, and document indexing.
"""
import logging
from flask import Flask
from flask_cors import CORS

from config import CONFIG
from engine import SearchEngine
from routes import api
from load_trie import get_trie

# Configure logging with more detail
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG for more detail
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
    ]
)
logger = logging.getLogger(__name__)

# Set Flask's logger to be more verbose
logging.getLogger('werkzeug').setLevel(logging.DEBUG)


def create_app() -> Flask:
    """
    Application factory for creating the Flask app.
    
    Returns:
        Flask: Configured Flask application instance
    """
    app = Flask(__name__)
    
    # Enable CORS for all routes
    CORS(app)
    
    # Initialize search engine
    logger.info("Initializing BigSearch Engine...")
    try:
        engine = SearchEngine()
        engine.initialize()
        
        # Store engine in app context for access in routes
        app.config['search_engine'] = engine
        
        logger.info("BigSearch Engine initialized successfully")
        logger.info(f"Engine state: {engine.get_state()}")
    except Exception as e:
        logger.error(f"Failed to initialize search engine: {e}")
        raise
    
    # Initialize autocomplete trie
    logger.info("Loading autocomplete trie...")
    try:
        trie = get_trie()
        trie_loaded = trie.load()
        
        # Store trie in app context
        app.config['autocomplete_trie'] = trie
        
        if trie_loaded:
            logger.info("Autocomplete trie loaded successfully")
        else:
            logger.warning("Autocomplete trie not available")
    except Exception as e:
        logger.warning(f"Failed to load autocomplete trie: {e}")
        app.config['autocomplete_trie'] = None
    
    # Register blueprints
    app.register_blueprint(api, url_prefix='/api')
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {'status': 'healthy', 'service': 'BigSearch API'}
    
    # Root endpoint
    @app.route('/')
    def root():
        return {
            'name': 'BigSearch API',
            'version': '1.0.0',
            'endpoints': {
                'search': '/api/search?q=<query>',
                'autocomplete': '/api/autocomplete?q=<prefix>',
                'index_html': 'POST /api/index/html',
                'index_json': 'POST /api/index/json',
                'index_pdf': 'POST /api/index/pdf',
                'status': '/api/status',
                'health': '/health',
                'save': 'POST /api/save (manual save all data)'
            }
        }
    
    return app


def main():
    """Main entry point for running the server."""
    app = create_app()
    
    logger.info(f"Starting BigSearch Server on port {CONFIG['PORT']}...")
    logger.info("Press Ctrl+C to stop the server")
    logger.info("Error tracebacks will be printed to stderr")
    try:
        app.run(
            host='0.0.0.0',
            port=CONFIG['PORT'],
            debug=True,  # Enable debug mode for better error messages
            use_reloader=False  # Disable reloader to prevent double initialization
        )
    except KeyboardInterrupt:
        logger.info("BigSearch Server shutting down...")
        print(f"Systematic Shutdown in progress... Preserving data")
        app.config['search_engine'].shutdown()


if __name__ == '__main__':
    main()
