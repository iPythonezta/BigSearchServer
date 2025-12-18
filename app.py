"""
BigSearch Server - Main Application Entry Point

A Flask-based REST API server for the BigSearch search engine.
Provides endpoints for searching, autocomplete, and document indexing.
"""
import logging
from flask import Flask
from flask_cors import CORS
from flask import send_from_directory
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
    import os

    dist_path = os.path.join(os.path.dirname(__file__), "dist")

    app = Flask(
        __name__,
        static_folder=dist_path,
        static_url_path=""
    )

    
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
    # Serve frontend index.html
    @app.route("/")
    def serve_index():
        return send_from_directory(app.static_folder, "index.html")


    # SPA fallback: serve index.html for non-API routes
    @app.route("/<path:path>")
    def serve_static_or_index(path):
        # Never hijack API routes
        if path.startswith("api/"):
            return {"error": "Not Found"}, 404
    
        file_path = os.path.join(app.static_folder, path)
    
        if os.path.exists(file_path):
            return send_from_directory(app.static_folder, path)
    
        # SPA fallback
        return send_from_directory(app.static_folder, "index.html")
    
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
