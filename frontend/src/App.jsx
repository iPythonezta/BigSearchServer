import React, { useState, useRef } from 'react';
import SearchBar from './components/SearchBar';
import SearchResults from './components/SearchResults';
import AddDocumentForm from './components/AddDocumentForm';
import { searchDocuments } from './api/search';

const App = () => {
  const [results, setResults] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  
  // Toggles
  const [semanticEnabled, setSemanticEnabled] = useState(false);
  
  const [currentQuery, setCurrentQuery] = useState('');

  const latestRequestRef = useRef(0);

  const handleSearch = async (query) => {
    setCurrentQuery(query);
    if (!query || !query.trim()) {
      setResults(null);
      setHasSearched(false);
      return;
    }

    const requestId = Date.now();
    latestRequestRef.current = requestId;

    setHasSearched(true);
    setIsLoading(true);

    try {
      const data = await searchDocuments({
        query,
        semantic: semanticEnabled
      });

      if (latestRequestRef.current === requestId) {
        setResults(data);
        setIsLoading(false);
      }
    } catch (err) {
      if (latestRequestRef.current === requestId) {
        setIsLoading(false);
      }
    }
  };

  // Re-run search when semantic toggle changes
  React.useEffect(() => {
    if (currentQuery) {
      handleSearch(currentQuery);
    }
  }, [semanticEnabled]);

  const handleDocAdded = (newDoc) => {
    // If we have an active query, re-run search to see if new doc appears
    if (currentQuery) {
      handleSearch(currentQuery);
    }
  };

  return (
    <div className={`app-container ${hasSearched ? 'top-aligned' : 'centered'}`}>
      <h1 className="app-title">BigSearch</h1>
      
      <SearchBar 
        onSearch={handleSearch} 
        semanticEnabled={semanticEnabled}
        setSemanticEnabled={setSemanticEnabled}
      />
      
      <SearchResults 
        results={results} 
        isLoading={isLoading} 
        hasSearched={hasSearched} 
      />
      
      <AddDocumentForm onDocAdded={handleDocAdded} />
    </div>
  );
};

export default App;