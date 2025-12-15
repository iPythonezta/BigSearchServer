"""
BigSearch Server Configuration
==============================
Central configuration for the Flask server and search engine.
"""

import os

# Base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Data directories
DATA_DIR = os.path.join(BASE_DIR, "data")
BARRELS_DIR = os.path.join(DATA_DIR, "barrels")
RANKINGS_DIR = os.path.join(DATA_DIR, "rankings")
SEMANTIC_DIR = os.path.join(DATA_DIR, "semantic")
MAPPINGS_DIR = os.path.join(DATA_DIR, "mappings")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
MODELS_DIR = os.path.join(DATA_DIR, "models")
MEMORY_BARRELS_DIR = os.path.join(DATA_DIR, "mem_barrels")

# Cache settings
WORD_CACHE_SIZE = 500
WORD_CACHE_FILE = os.path.join(DATA_DIR, "word_cache.msgpack")
AUTO_SAVE_INTERVAL = 50

# State file (tracks document IDs for dynamic indexing)
STATE_FILE = os.path.join(DATA_DIR, "engine_state.json")

# Server settings
DEBUG = True
HOST = "0.0.0.0"
PORT = 5000

# Search settings
DEFAULT_SEMANTIC_WEIGHT = 20
DEFAULT_USE_SEMANTIC = True

# CORS settings
CORS_ORIGINS = ["*"]  # Allow all origins in development

# File upload settings
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB max upload
ALLOWED_EXTENSIONS = {
    'pdf': {'pdf'},
    'json': {'json'},
    'html': {'html', 'htm'}
}

CONFIG = {
    'PORT': PORT,
    'DEBUG': DEBUG,
}