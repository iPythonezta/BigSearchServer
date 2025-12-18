import React from 'react';

const AutocompleteDropdown = ({ 
  suggestions, 
  activeIndex, 
  onSelect 
}) => {
  if (!suggestions || suggestions.length === 0) return null;

  return (
    <div className="autocomplete-dropdown">
      {suggestions.map((suggestion, index) => (
        <div
          key={suggestion}
          className={`autocomplete-item ${index === activeIndex ? 'active' : ''}`}
          onClick={(e) => {
            e.preventDefault();
            onSelect(suggestion);
          }}
        >
          {suggestion}
        </div>
      ))}
    </div>
  );
};

export default AutocompleteDropdown;