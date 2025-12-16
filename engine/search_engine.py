"""
BigSearch Search Engine Module
==============================
Core search engine with word-level caching, keyword scoring, and semantic search.
Ported from hybrid_search.py for server usage.
"""

import os
import re
import math
import numpy as np
import pandas as pd
import ormsgpack
import orjson
from urllib.parse import urlparse
from collections import Counter, defaultdict, OrderedDict
from typing import Dict, List, Optional, Any
from MMapBarrel.MMapBarrel import MMapBarrel
from MMapBarrel.LSMBarrel import LSMBarrel
from FileHandler.file_handler import FileHandler
from gensim.models import KeyedVectors
import config


class SearchEngine:
    """
    BigSearch Hybrid Search Engine
    Combines keyword-based search with semantic similarity scoring.
    """
    
    def __init__(self):
        """Initialize the search engine and load all required data."""
        self.initialized = False
        self.semantic_available = False
        
        # Word-level cache
        self.word_cache = OrderedDict()
        self._cache_updates_since_save = 0
        
        # Data stores
        self.barrels_index = {}
        self.doc_id_to_url = {}
        self.page_rank_dict = {}
        self.domain_rank_dict = {}
        self.citation_dict = {}
        self.rps_info_dict = {}
        self.idf_map = {}
        self.temporary_associations = {} # Word to temporary document associations
        self.pending_additions_per_barrel = defaultdict(int)
        self.words_pending_additions_barrel = defaultdict(set)
        
        # Semantic search data
        self.word2vec_model = None
        self.merged_embeddings_np = None
        self.html_docs_count = 0
        self.json_docs_count = 0
        
        # State tracking for dynamic indexing
        self.state = {
            "last_html_id": 0,
            "last_json_id": 0,
            "total_documents": 0
        }
        
    def initialize(self) -> bool:
        """
        Load all data files and initialize the search engine.
        Returns True if successful.
        """
        try:
            print("Loading BigSearch Server Engine...")
            
            # Load page rank data
           
            # Create rank dictionaries
            print("  → Creating rank dictionaries...")
            with open(os.path.join(config.RANKINGS_DIR, "citation_ranks.json"), "rb") as f:
                self.citation_dict = orjson.loads(f.read())
            
            with open(os.path.join(config.RANKINGS_DIR, "page_rank_dict.json"), "rb") as f:
                self.page_rank_dict = orjson.loads(f.read())
            
            with open(os.path.join(config.RANKINGS_DIR, "domain_rank_dict.json"), "rb") as f:
                self.domain_rank_dict = orjson.loads(f.read())
            
            # Load research paper info
            print("  → Loading research paper info...")
            with open(os.path.join(config.MAPPINGS_DIR, "rps_info.json"), "rb") as f:
                self.rps_info_dict = orjson.loads(f.read())

            
            # Load URL mappings
            print("  → Loading URL mappings...")
            with open(os.path.join(config.MAPPINGS_DIR, "ind_to_url.json"), "r") as f:
                self.doc_id_to_url = orjson.loads(f.read())
            
            # Load barrel index
            print("  → Loading barrel index...")
            with open(os.path.join(config.BARRELS_DIR, "barrels_index.json"), "r", encoding="utf-8") as f:
                self.barrels_index = orjson.loads(f.read())

            print(" → Loading barrels into memory-mapped format...")
            self.mmap_barrels = {}
            for barrles_fname in os.listdir(config.MEMORY_BARRELS_DIR):
                if barrles_fname.startswith("barrel_"):
                    barrel_id = barrles_fname.split("_")[1]
                    barrel_path = os.path.join(config.MEMORY_BARRELS_DIR, barrles_fname)
                    self.mmap_barrels[int(barrel_id)] = LSMBarrel(barrel_path)

            
            # Load semantic search data
            print("  → Loading semantic search data...")
            try:
                self.html_embeddings = orjson.loads(
                    open(os.path.join(config.SEMANTIC_DIR, "html_embeddings.json"), 'rb').read()
                )
                self.json_embeddings = orjson.loads(
                    open(os.path.join(config.SEMANTIC_DIR, "json_embeddings.json"), 'rb').read()
                )
                self.idf_map = orjson.loads(
                    open(os.path.join(config.SEMANTIC_DIR, "idf_map.json"), 'rb').read()
                )
                
                self.word2vec_model = KeyedVectors.load_word2vec_format(
                    os.path.join(config.MODELS_DIR, "fine_tunned_model.word2vec.txt"),
                    binary=False
                )
                
                self._initialize_norms()
                
                self.semantic_available = True
                print("  ✓ Semantic search enabled")
            except Exception as e:
                print(f"  ⚠ Semantic search unavailable: {e}")
                self.semantic_available = False
            
            # Load word cache
            self._load_word_cache()
            
            # Load engine state
            self._load_state()
            
            # Update state with current document counts
            self.state["last_html_id"] = self.html_docs_count
            self.state["last_json_id"] = self.json_docs_count
            self.state["total_documents"] = self.html_docs_count + self.json_docs_count
            
            self.initialized = True
            print("✓ BigSearch Server Engine loaded successfully!\n")
            return True
            
        except Exception as e:
            print(f"✗ Failed to initialize search engine: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _initialize_norms(self):
            merged_embeddings = self.html_embeddings + self.json_embeddings
            self.html_docs_count = len(self.html_embeddings)
            self.json_docs_count = len(self.json_embeddings)
            self.merged_embeddings_np = np.array(merged_embeddings)
            self.doc_norms = np.linalg.norm(self.merged_embeddings_np, axis=1)
            self.doc_norms[self.doc_norms == 0] = 1
    
    def _load_word_cache(self):
        """Load word cache from disk if exists."""
        print("  → Initializing word-level cache...")
        try:
            if os.path.exists(config.WORD_CACHE_FILE):
                print(f"    → Loading cached words from {config.WORD_CACHE_FILE}...")
                with open(config.WORD_CACHE_FILE, "rb") as f:
                    cache_data = ormsgpack.unpackb(f.read())
                    self.word_cache = OrderedDict(cache_data.get("cache", {}))
                print(f"    ✓ Loaded {len(self.word_cache)} cached words")
        except Exception as e:
            print(f"    ⚠ Could not load word cache: {e}")
            self.word_cache = {}
            self.word_cache_stack = []
    
    def save_word_cache(self):
        """Save word cache to disk for persistence."""
        try:
            cache_data = {
                "cache": self.word_cache,
            }
            os.makedirs(os.path.dirname(config.WORD_CACHE_FILE), exist_ok=True)
            with open(config.WORD_CACHE_FILE, "wb") as f:
                f.write(ormsgpack.packb(cache_data))
            print(f"✓ Saved {len(self.word_cache)} words to cache")
        except Exception as e:
            print(f"⚠ Could not save word cache: {e}")
    
    def _load_state(self):
        """Load engine state from disk."""
        try:
            if os.path.exists(config.STATE_FILE):
                with open(config.STATE_FILE, "r") as f:
                    self.state = orjson.loads(f.read())
                print(f"    ✓ Loaded engine state")
        except Exception as e:
            print(f"    ⚠ Could not load state: {e}")
    
    def save_state(self):
        """Save engine state to disk."""
        try:
            os.makedirs(os.path.dirname(config.STATE_FILE), exist_ok=True)
            with open(config.STATE_FILE, "wb") as f:
                f.write(orjson.dumps(self.state))
        except Exception as e:
            print(f"⚠ Could not save state: {e}")
    
    def get_state(self) -> Dict:
        """Get current engine state."""
        return {
            **self.state,
            "semantic_available": self.semantic_available,
            "cached_words": len(self.word_cache),
            "initialized": self.initialized
        }
    
    # ==================== WORD LOOKUP ====================
    
    def word_lookup(self, word: str, indices: List) -> List:
        """Load a word's posting list from barrel with word-level caching."""
        if word in self.word_cache:

            self.word_cache.move_to_end(word)
            extra = self.temporary_associations.get(word, [])
            return self.word_cache[word] + extra
        
        barrel_id = indices[0]
        word_index = indices[1]
        posting_list = self.mmap_barrels[barrel_id].get_posting(word_index)
        self.word_cache[word] = posting_list
        
        if len(self.word_cache) > config.WORD_CACHE_SIZE:
            self.word_cache.popitem(last=False)

        self._cache_updates_since_save += 1
        if self._cache_updates_since_save >= config.AUTO_SAVE_INTERVAL:
            self.save_word_cache()
            self._cache_updates_since_save = 0
        
        extra = self.temporary_associations.get(word, [])

        return posting_list + extra
    
    # ==================== TEXT PROCESSING ====================
    
    @staticmethod
    def normalize_title(title: str) -> str:
        """Normalize research paper titles for matching."""
        title = title.lower()
        title = re.sub(r'\(.*?\)|\[.*?\]|\{.*?\}|<.*?>', ' ', title)
        title = re.sub(r'[^a-z\s]', ' ', title)
        title = re.sub(r'\s+', ' ', title)
        return title.strip()
    
    @staticmethod
    def process_query(word: str, rps: bool = True) -> List[str]:
        """Tokenize and normalize query text."""
        text = re.sub(r'\n', ' ', word)
        if rps:
            text = re.sub(r'(?<!\d)[^\w\s]|[^\w\s](?!\d)', '', text)
        else:
            text = re.sub(r'(?<!\d)[^\w\s]|[^\w\s](?!\d)', ' ', text)
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"[,\(\)\[\]\{\}]", "", text)
        text = text.lower()
        tokens = text.split(' ')
        return tokens
    
    # ==================== SCORING FUNCTIONS ====================
    
    def score_html_files(self, hitlist: List) -> int:
        """Score HTML documents based on keyword occurrence."""
        doc_id = hitlist[0]
        positions = hitlist[1]
        hit_counter = hitlist[2]

        n_title = hit_counter[0]
        n_meta = hit_counter[1]
        n_heading = hit_counter[2]
        n_total = hit_counter[3]
        n_href = hit_counter[4]
        in_domain = hit_counter[5]
        in_url = hit_counter[6]
        doc_len = hit_counter[7] if hit_counter[7] > 0 else 1

        score = 0.0

        # Zone weighting
        score += min(n_title * 7.5, 15)
        if in_domain:
            score += 10
        if in_url:
            score += 5
        score += min(n_heading * 3, 9)
        score += min(n_meta * 2, 6)

        # Position bonus
        if positions:
            first_pos = positions[0]
            score += 15 - min(first_pos // 7, 15)

        # Frequency scoring with density penalty
        body_hits = max(0, n_total - (n_title + n_heading + n_meta))
        density = n_total / doc_len
        freq_score = math.log(1 + body_hits) * 7
        score += min(freq_score, 20)
        score *= (1 - density)

        # Final clamping
        final_score = max(1.0, min(80.0, score))

        # Add PageRank and DomainRank
        doc_url = self.doc_id_to_url.get(doc_id.replace("H", ""), "")
        page_rank_score = self.page_rank_dict.get(doc_url, 0)
        domain = urlparse(doc_url).netloc
        domain_rank_score = self.domain_rank_dict.get(domain, 0)

        return int(final_score + page_rank_score + domain_rank_score)
    
    def rank_research_papers(self, hitlist: List) -> int:
        """Score research papers based on keyword occurrence."""
        doc_id = hitlist[0]
        positions = hitlist[1]
        hit_counter = hitlist[2]

        n_golden = hit_counter[0]
        n_body = hit_counter[1]
        n_other = hit_counter[2]
        n_total = hit_counter[3]
        doc_len = hit_counter[4]

        score = 0.0

        # Golden zone (title, author, abstract)
        score += min(n_golden * 5, 35)

        # Position bonus
        if positions:
            first_pos = positions[0]
            score += 15 - min(first_pos // 15, 10)

        # Body frequency with density penalty
        density = n_total / doc_len
        relevant_hits = n_body + (n_other * 0.1)
        freq_score = math.log(1 + relevant_hits) * 10
        score += min(freq_score, 40)
        score *= (1 - density)

        # Final clamping
        final_score = max(1.0, min(80.0, score))

        # Add citation rank
        title = self.rps_info_dict.get(str(doc_id.replace("P", "")), ("", ""))[0].strip()
        title = self.normalize_title(title)
        citation_rank_score = self.citation_dict.get(title, 0)

        return int(final_score + citation_rank_score)
    
    # ==================== SEMANTIC SEARCH ====================
    
    @staticmethod
    def compute_tf(tokens: List[str]) -> Dict[str, float]:
        """Compute term frequency for query tokens."""
        counts = Counter(tokens)
        total = sum(counts.values())
        tf_map = {word: count / total for word, count in counts.items()}
        return tf_map
    
    def query_to_embedding(self, tokens: List[str]) -> np.ndarray:
        """Convert query tokens to embedding vector using TF-IDF weighting."""
        tf_map = self.compute_tf(tokens)
        vecs, weights = [], []
        for word, tf in tf_map.items():
            if word in self.word2vec_model:
                tfidf = tf * self.idf_map.get(word, 0)
                vecs.append(self.word2vec_model[word] * tfidf)
                weights.append(tfidf)
        if not vecs:
            return np.zeros(self.word2vec_model.vector_size)
        return np.sum(vecs, axis=0) / np.sum(weights)
    
    def convert_ind_to_doc_id(self, index: int) -> str:
        """Convert embedding index to document ID."""
        if index < self.html_docs_count:
            return f"H{index}"
        else:
            return f"P{index - self.html_docs_count}"
    
    def get_semantic_scores(self, query: str) -> Dict[str, float]:
        """Get semantic similarity scores for all documents using vectorized operations."""
        if not self.semantic_available:
            return {}
        
        text = query.lower()
        text = re.sub(r'[^a-z0-9\s]', '', text)
        tokens = text.split()
        
        query_vec = self.query_to_embedding(tokens)
        
        # Vectorized cosine similarity calculation
        query_norm = np.linalg.norm(query_vec)
        if query_norm == 0:
            return {}
        
        query_normalized = query_vec / query_norm
        similarities_array = np.dot(self.merged_embeddings_np, query_normalized) / self.doc_norms
        
        # Convert to dictionary
        similarities = {
            self.convert_ind_to_doc_id(i): float(sim) 
            for i, sim in enumerate(similarities_array)
        }
        
        return similarities
    
    # ==================== MAIN SEARCH ====================
    
    def search(self, query: str, use_semantic: bool = True, semantic_weight: int = 20) -> List[Dict]:
        """
        Perform hybrid search combining keyword and semantic scoring.
        
        Args:
            query: Search query string
            use_semantic: Whether to include semantic scores
            semantic_weight: Multiplier for semantic scores
        
        Returns:
            List of result dictionaries sorted by score
        """
        if not self.initialized:
            return []
        
        tokens_rps = [tok for tok in self.process_query(query, rps=True) if tok in self.barrels_index]
        tokens_html = [tok for tok in self.process_query(query, rps=False) if tok in self.barrels_index]

        token_hitlists = []

        # Build hitlists - separate for each document type
        for token in set(tokens_rps + tokens_html):
            htl = self.word_lookup(token, self.barrels_index[token])
            token_hitlists.append((token, htl))

        # Semantic only search
        if not token_hitlists:
            if not (use_semantic and self.semantic_available):
                return []

            semantic_scores = self.get_semantic_scores(query)
            results = []

            for doc_id, sem_score in semantic_scores.items():
                if sem_score <= 0:
                    continue

                url = (
                    self.rps_info_dict.get(str(doc_id[1:]), ("", ""))[1]
                    if doc_id.startswith("P")
                    else self.doc_id_to_url.get(doc_id[1:], "")
                )

                results.append({
                    "doc_id": doc_id,
                    "final_score": semantic_weight * sem_score,
                    "keyword_score": 0,
                    "semantic_score": sem_score,
                    "avg_word_score": 0,
                    "phrase_bonus": 0,
                    "url": url,
                    "positions": []
                })

            return sorted(results, key=lambda x: x["final_score"], reverse=True)

        # Intersection - separate by document type
        rps_hitlists = [(token, htl) for token, htl in token_hitlists if token in tokens_rps]
        html_hitlists = [(token, htl) for token, htl in token_hitlists if token in tokens_html]

        common_doc_ids = set()

        # Process research papers
        if rps_hitlists:
            rps_hitlists.sort(key=lambda x: len(x[1]))
            rps_common = {hit[0] for hit in rps_hitlists[0][1] if hit[0].startswith("P")}
            for token, hitlist in rps_hitlists[1:]:
                rps_common &= {hit[0] for hit in hitlist if hit[0].startswith("P")}
            common_doc_ids |= rps_common

        # Process HTML documents
        if html_hitlists:
            html_hitlists.sort(key=lambda x: len(x[1]))
            html_common = {hit[0] for hit in html_hitlists[0][1] if hit[0].startswith("H")}
            for _, hitlist in html_hitlists[1:]:
                html_common &= {hit[0] for hit in hitlist if hit[0].startswith("H")}
            common_doc_ids |= html_common

        if not common_doc_ids:
            semantic_scores = self.get_semantic_scores(query) if use_semantic and self.semantic_available else {}
            if not semantic_scores:
                return []
            # Return semantic-only results
            results = []
            for doc_id, sem_score in semantic_scores.items():
                if sem_score <= 0:
                    continue

                url = (
                    self.rps_info_dict.get(str(doc_id[1:]), ("", ""))[1]
                    if doc_id.startswith("P")
                    else self.doc_id_to_url.get(doc_id[1:], "")
                )

                results.append({
                    "doc_id": doc_id,
                    "final_score": semantic_weight * sem_score,
                    "keyword_score": 0,
                    "semantic_score": sem_score,
                    "avg_word_score": 0,
                    "phrase_bonus": 0,
                    "url": url,
                    "positions": []
                })

        # Rebuild intersected results
        intersected = defaultdict(list)

        for token, hitlist in token_hitlists:
            for hit in hitlist:
                if hit[0] in common_doc_ids:
                    intersected[hit[0]].append((token, hit))

        semantic_scores = self.get_semantic_scores(query) if use_semantic and self.semantic_available else {}

        ranked = []

        # Scoring
        for doc_id, token_hits in intersected.items():
            tokens = tokens_rps if doc_id.startswith("P") else tokens_html
            if not tokens:
                continue
            word_scores = []
            token_positions = defaultdict(list)
            all_positions = []
            
            for token, hit in token_hits:
                score = self.rank_research_papers(hit) if doc_id.startswith("P") else self.score_html_files(hit)
                word_scores.append(score)

                pos = hit[1]
                token_positions[token].extend(pos)
                all_positions.extend(pos)

            avg_word_score = sum(word_scores) / (len(word_scores))

            # Phrase bonus
            phrase_bonus = 0
            first_token = tokens[0]

            for start in token_positions[first_token]:
                curr = start
                length = 1

                for token in tokens[1:]:
                    nxt = next((p for p in token_positions[token] if 0 < p - curr <= 2), None)
                    if nxt is None:
                        break
                    curr = nxt
                    length += 1

                phrase_bonus += sum(range(length))

            keyword_score = avg_word_score + phrase_bonus
            semantic_score = semantic_scores.get(doc_id, 0.0)

            final_score = keyword_score + semantic_weight * semantic_score

            url = (
                self.rps_info_dict.get(str(doc_id[1:]), ("", ""))[1]
                if doc_id.startswith("P")
                else self.doc_id_to_url.get(doc_id[1:], "")
            )

            ranked.append({
                "doc_id": doc_id,
                "final_score": final_score,
                "keyword_score": keyword_score,
                "semantic_score": semantic_score,
                "avg_word_score": avg_word_score,
                "phrase_bonus": phrase_bonus,
                "url": url,
                "positions": all_positions
            })

        return sorted(ranked, key=lambda x: x["final_score"], reverse=True)

    def index_new_rps(self, file_content, url):
        """
        Incrementally index a new research paper (RPS).
        Keyword index goes to delta barrels.
        Embedding goes to semantic store.
        """

        # ---- 1. Assign ID safely ----
        new_id = self.state["last_json_id"]
        doc_id = f"P{new_id}"
        self.state["last_json_id"] += 1
        self.state["total_documents"] += 1

        # ---- 2. Save file ----
        file_name = f"{doc_id}.json"
        title = ""
        try:
            title = orjson.loads(file_content)["metadata"]["title"]
        except KeyError:
            pass
        rp_path = FileHandler.save_temp_file_rp(file_content, file_name)

        # ---- 3. Keyword indexing (DELTA) ----
        hitlists = FileHandler.process_json_file(rp_path)
        for word, hitlist in hitlists.items():
            if word in self.barrels_index:
                barrel = self.barrels_index[word][0]
                self.pending_additions_per_barrel[barrel] += 1
                self.words_pending_additions_barrel[barrel].add(word)
                self.temporary_associations.setdefault(word, []).append(hitlist)

        # ---- 4. Semantic embedding ----
        text = FileHandler.extract_text_from_json(rp_path)
        tokens = FileHandler.preprocess_text(text)
        doc_embedding = self.query_to_embedding(tokens)

        self.json_embeddings.append(doc_embedding.tolist())

        # ---- 5. Update semantic matrices ----
        self.merged_embeddings_np = np.vstack([
            self.merged_embeddings_np,
            doc_embedding
        ])

        self.doc_norms = np.linalg.norm(self.merged_embeddings_np, axis=1)
        self.doc_norms[self.doc_norms == 0] = 1
        self.rps_info_dict[str(new_id)] = (title, url)

        return doc_id
    
    def merge_in_bg(self, barrel_id):
        if barrel_id not in self.pending_additions_per_barrel:
            return

        barrel = self.mmap_barrels[barrel_id]

        for word in self.words_pending_additions_barrel[barrel_id]:
            if word in self.temporary_associations:
                idx = self.barrels_index[word][1]
                barrel.append_delta(idx, self.temporary_associations[word])
                del self.temporary_associations[word]

        self.pending_additions_per_barrel[barrel_id] = 0


    
    def shutdown(self):
        """Cleanup on shutdown - save cache and state."""
        print("Shutting down search engine...")
        self.save_word_cache()
        self.save_state()
        # Dump everything into disk
        with open(os.path.join(config.SEMANTIC_DIR, "json_embeddings.json"), "wb") as f:
            f.write(orjson.dumps(self.json_embeddings))

        with open(os.path.join(config.SEMANTIC_DIR, "html_embeddings.json"), "wb") as f:
            f.write(orjson.dumps(self.html_embeddings))

        # Save all words into barrel
        for barrel_id in list(self.pending_additions_per_barrel.keys()):
            self.merge_in_bg(barrel_id)
        
        # Save all dicts to json

        with open(os.path.join(config.MAPPINGS_DIR, "rps_info.json"), "wb") as f:
            f.write(orjson.dumps(self.rps_info_dict))
        
        with open(os.path.join(config.MAPPINGS_DIR, "ind_to_url.json"), "wb") as f:
            f.write(orjson.dumps(self.doc_id_to_url))

        print("✓ Search engine shutdown complete")

