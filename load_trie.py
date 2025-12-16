"""
BigSearch Autocomplete Module
==============================
Trie-based autocomplete system for query suggestions.
"""

import msgpack
import os


class TrieNode:
    __slots__ = ("children", "word", "tf")

    def __init__(self):
        self.children = {}
        self.word = None
        self.tf = 0


class AutocompleteTrie:
    
    def __init__(self, trie_path: str = "data/autocomplete/autocomplete_trie.msgpack"):
        self.root = None
        self.trie_path = trie_path
        self.loaded = False
    
    def load(self) -> bool:
        """
        Load the trie from disk.
        
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            if not os.path.exists(self.trie_path):
                print(f"⚠ Autocomplete trie not found at {self.trie_path}")
                return False
            
            with open(self.trie_path, "rb") as f:
                packed = msgpack.unpackb(f.read(), raw=False)
            
            self.root = self._deserialize(packed)
            self.loaded = True
            print(f"Autocomplete trie loaded from {self.trie_path}")
            return True
            
        except Exception as e:
            print(f"Failed to load autocomplete trie: {e}")
            return False
    
    def _deserialize(self, data):
        node = TrieNode()
        node.word = data.get("w")
        node.tf = data.get("tf", 0)  # Use 'tf' not 't'
        for ch, child in data.get("c", {}).items():
            node.children[ch] = self._deserialize(child)
        return node
    
    def autocomplete(self, prefix: str, k: int = 5) -> list:

        if not self.loaded or not self.root:
            return []
        
        node = self.root
        for ch in prefix.lower():
            if ch not in node.children:
                return []
            node = node.children[ch]
        
        results = []
        
        def dfs(n):
            if n.word:
                results.append((n.word, n.tf))
            for child in n.children.values():
                dfs(child)
        
        dfs(node)
        
        results.sort(key=lambda x: x[1], reverse=True)
        return [w for w, _ in results[:k]]
    
    def split_query(self, query: str) -> tuple:

        parts = query.strip().split()
        if len(parts) == 0:
            return [], ""
        if len(parts) == 1:
            return [], parts[0].lower()
        return parts[:-1], parts[-1].lower()
    
    def suggest(self, query: str, k: int = 5) -> list:
        if not self.loaded:
            return []
        
        context, last = self.split_query(query)
        completions = self.autocomplete(last, k=k)
        
        suggestions = [
            " ".join(context + [w]) for w in completions
        ]
        
        return suggestions


# Global trie instance
_trie_instance = None


def get_trie() -> AutocompleteTrie:
    """Get the global autocomplete trie instance."""
    global _trie_instance
    if _trie_instance is None:
        _trie_instance = AutocompleteTrie()
    return _trie_instance


def load_trie() -> bool:
    """Load the global trie instance."""
    trie = get_trie()
    return trie.load()
