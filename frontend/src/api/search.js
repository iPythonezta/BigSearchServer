const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api';

/**
 * Search documents using the backend API
 * @param {Object} params - Search parameters
 * @param {string} params.query - Search query string
 * @param {boolean} params.semantic - Whether to use semantic search (default: false)
 * @param {number} params.semantic_weight - Weight for semantic scores (default: 20)
 * @returns {Promise<Array>} Array of search results
 */
export async function searchDocuments({ query, semantic = false, semantic_weight = 20 }) {
  if (!query || !query.trim()) {
    return [];
  }

  try {
    const response = await fetch(`${API_BASE_URL}/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: query.trim(),
        use_semantic: semantic,
        semantic_weight: semantic_weight,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `Search failed: ${response.statusText}`);
    }

    const data = await response.json();
    
    if (data.success === false) {
      throw new Error(data.error || 'Search request failed');
    }

    // Return results array (backend returns { success: true, results: [...] })
    return data.results || [];
  } catch (error) {
    console.error('Search error:', error);
    // Return empty array on error (graceful degradation)
    return [];
  }
}