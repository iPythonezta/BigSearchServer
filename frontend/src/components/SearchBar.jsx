import React, { useState, useEffect, useRef } from 'react';
import { getAutocompleteSuggestions } from '../api/autocomplete';
import AutocompleteDropdown from './AutocompleteDropdown';

const SearchBar = ({ onSearch, semanticEnabled, setSemanticEnabled }) => {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [showDropdown, setShowDropdown] = useState(false);
  
  const inputRef = useRef(null);
  const debounceTimerRef = useRef(null);

  const getLastToken = (text) => {
    const tokens = text.split(/\s+/);
    return tokens[tokens.length - 1];
  };

  const handleChange = (e) => {
    const val = e.target.value;
    setQuery(val);
    setShowDropdown(true);

    if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);

    // Trigger search debounce
    debounceTimerRef.current = setTimeout(() => {
      onSearch(val);
    }, 400);

    // Trigger autocomplete separately
    const token = getLastToken(val);
    if (token && token.length >= 2) {
      getAutocompleteSuggestions(token).then(results => {
        setSuggestions(results);
        setActiveIndex(-1);
      });
    } else {
      setSuggestions([]);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (suggestions.length > 0) {
        setActiveIndex((prev) => (prev + 1) % suggestions.length);
      }
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (suggestions.length > 0) {
        setActiveIndex((prev) => (prev - 1 + suggestions.length) % suggestions.length);
      }
    } else if (e.key === 'Enter') {
      if (activeIndex >= 0 && showDropdown && suggestions.length > 0) {
        e.preventDefault();
        handleSelect(suggestions[activeIndex]);
      } else {
        setShowDropdown(false);
        onSearch(query);
        inputRef.current?.blur();
      }
    } else if (e.key === 'Escape') {
      setShowDropdown(false);
      inputRef.current?.blur();
    }
  };

  const handleSelect = (suggestion) => {
    const tokens = query.split(/\s+/);
    tokens.pop(); 
    tokens.push(suggestion);
    
    const newQuery = tokens.join(' ') + ' '; 
    setQuery(newQuery);
    setShowDropdown(false);
    setSuggestions([]);
    
    // Trigger immediate search on selection
    onSearch(newQuery);
    inputRef.current?.focus();
  };

  return (
    <div className="search-section">
      <div className="search-wrapper">
        <input
          ref={inputRef}
          type="text"
          className="search-input"
          placeholder="What's on your mind?"
          value={query}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onFocus={() => setShowDropdown(true)}
          onBlur={() => setTimeout(() => setShowDropdown(false), 200)} 
          autoComplete="off"
        />
        
        {showDropdown && suggestions.length > 0 && (
          <AutocompleteDropdown
            suggestions={suggestions}
            activeIndex={activeIndex}
            onSelect={handleSelect}
          />
        )}
      </div>

      <div className="search-controls">
        <label className="toggle-label">
          <input
            type="checkbox"
            className="toggle-input"
            checked={semanticEnabled}
            onChange={(e) => setSemanticEnabled(e.target.checked)}
          />
          <span>Semantic Search</span>
        </label>
      </div>
    </div>
  );
};

export default SearchBar;