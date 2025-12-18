const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api';

/**
 * Get autocomplete suggestions from the backend API
 * @param {string} prefix - Prefix to autocomplete
 * @param {number} limit - Maximum number of suggestions (default: 5)
 * @returns {Promise<Array<string>>} Array of suggestion strings
 */
export async function getAutocompleteSuggestions(prefix, limit = 5) {
  if (!prefix || prefix.trim().length < 1) {
    return [];
  }

  try {
    const encodedPrefix = encodeURIComponent(prefix.trim());
    const response = await fetch(
      `${API_BASE_URL}/autocomplete?q=${encodedPrefix}&limit=${limit}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    // Fail silently on errors (as per requirements)
    if (!response.ok) {
      return [];
    }

    const data = await response.json();
    
    // Return suggestions array (backend returns { success: true, suggestions: [...] })
    return data.suggestions || [];
  } catch (error) {
    // Fail silently on network errors
    console.debug('Autocomplete error (silently ignored):', error);
    return [];
  }
}