import React, { useMemo, useState, useEffect } from 'react';
import ResultItem from './ResultItem';

const ITEMS_PER_PAGE = 10;

const SearchResults = ({ results, isLoading, hasSearched }) => {
  const [currentPage, setCurrentPage] = useState(1);

  // Reset to page 1 when new results arrive
  useEffect(() => {
    setCurrentPage(1);
  }, [results]);

  // Calculate max score from ALL results for proper normalization across pages
  const maxScore = useMemo(() => {
    if (!results || results.length === 0) return 1;
    return Math.max(...results.map(r => parseFloat(r.final_score) || 0));
  }, [results]);

  if (isLoading) {
    return <div className="loading">Searching knowledge base...</div>;
  }

  if (hasSearched && (!results || results.length === 0)) {
    return <div className="no-results">No documents found matching your query.</div>;
  }

  if (!results) return null;

  // Pagination Logic
  const indexOfLastItem = currentPage * ITEMS_PER_PAGE;
  const indexOfFirstItem = indexOfLastItem - ITEMS_PER_PAGE;
  const currentItems = results.slice(indexOfFirstItem, indexOfLastItem);
  const totalPages = Math.ceil(results.length / ITEMS_PER_PAGE);

  const handlePageChange = (pageNumber) => {
    setCurrentPage(pageNumber);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  /**
   * Generate pagination page numbers with Google-style collapsing
   * Rules:
   * - Always show first 10 pages
   * - Always show last page
   * - Show current page window (±2 pages around current)
   * - Collapse with ellipsis (...)
   */
  const generatePageNumbers = () => {
    if (totalPages <= 10) {
      // If 10 or fewer pages, show all
      return Array.from({ length: totalPages }, (_, i) => i + 1);
    }

    const pages = [];
    const FIRST_PAGES_COUNT = 10;
    const WINDOW_SIZE = 5; // Show ±2 pages around current

    // Always add first 10 pages
    for (let i = 1; i <= Math.min(FIRST_PAGES_COUNT, totalPages); i++) {
      pages.push(i);
    }

    // Calculate window around current page
    const windowStart = Math.max(1, currentPage - 2);
    const windowEnd = Math.min(totalPages, currentPage + 2);

    // Add pages around current if they're not already included
    for (let i = windowStart; i <= windowEnd; i++) {
      if (!pages.includes(i)) {
        pages.push(i);
      }
    }

    // Always add last page if not already included
    if (totalPages > FIRST_PAGES_COUNT && !pages.includes(totalPages)) {
      pages.push(totalPages);
    }

    // Sort and add ellipsis
    pages.sort((a, b) => a - b);
    const result = [];
    
    for (let i = 0; i < pages.length; i++) {
      const page = pages[i];
      const nextPage = pages[i + 1];
      
      result.push(page);
      
      // Add ellipsis if gap is more than 1
      if (nextPage && nextPage - page > 1) {
        result.push('ellipsis');
      }
    }

    return result;
  };

  const pageNumbers = generatePageNumbers();

  return (
    <div className="results-container">
      <div className="result-list">
        {currentItems.map((item, index) => (
          <ResultItem 
            key={item.doc_id || item.id || index} 
            result={item} 
            maxScore={maxScore}
          />
        ))}
      </div>

      {totalPages > 1 && (
        <div className="pagination">
          {/* Previous Button */}
          {currentPage > 1 && (
            <button 
              onClick={() => handlePageChange(currentPage - 1)}
              className="pagination-btn"
            >
              &lt; Prev
            </button>
          )}

          {/* Page Numbers */}
          {pageNumbers.map((page, index) => {
            if (page === 'ellipsis') {
              return (
                <span key={`ellipsis-${index}`} className="pagination-ellipsis">
                  …
                </span>
              );
            }
            
            return (
              <button
                key={page}
                onClick={() => handlePageChange(page)}
                className={`pagination-btn ${currentPage === page ? 'active' : ''}`}
              >
                {page}
              </button>
            );
          })}

          {/* Next Button */}
          {currentPage < totalPages && (
            <button 
              onClick={() => handlePageChange(currentPage + 1)}
              className="pagination-btn"
            >
              Next &gt;
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default SearchResults;