import React from 'react';

const ResultItem = ({ result, maxScore }) => {
  const { title, url, doc_id, final_score, keyword_score, semantic_score, phrase_bonus } = result;

  /**
   * Determine document type from doc_id prefix:
   * - "P" prefix = Research paper/PDF (indexed via /api/index/rps)
   * - "H" prefix = HTML document (indexed via /api/index/html)
   * - Unknown/other = "unknown"
   */
  const getBadgeType = () => {
    if (doc_id) {
      if (doc_id.startsWith('P')) {
        return 'pdf';  // Research papers/PDFs indexed via /api/index/rps
      } else if (doc_id.startsWith('H')) {
        return 'html';  // HTML documents indexed via /api/index/html
      }
    }
    return 'unknown'; 
  };

  const badgeType = getBadgeType();

  // Normalize final score relative to the query's top result
  const safeMax = maxScore > 0 ? maxScore : 1;
  const numericScore = parseFloat(final_score) || 0;
  const relevancePct = Math.min((numericScore / safeMax) * 100, 100);

  // Format scores to 3 decimal places, only show if present
  const formatScore = (score) => {
    if (score === null || score === undefined) return null;
    const num = parseFloat(score);
    return isNaN(num) ? null : num.toFixed(3);
  };

  const formattedSemanticScore = formatScore(semantic_score);
  const formattedKeywordScore = formatScore(keyword_score);
  const formattedPhraseBonus = formatScore(phrase_bonus);

  // Build stats array with only present scores
  const stats = [];
  if (formattedSemanticScore !== null) {
    stats.push({ label: 'Semantic Score', value: formattedSemanticScore });
  }
  if (formattedKeywordScore !== null) {
    stats.push({ label: 'Keyword Score', value: formattedKeywordScore });
  }
  if (formattedPhraseBonus !== null) {
    stats.push({ label: 'Phrase Bonus', value: formattedPhraseBonus });
  }

  return (
    <div className="result-card">
      <div className="result-main">
        <div className="result-header-row">
          <a href={url} target="_blank" rel="noopener noreferrer" className="result-title">
            {title}
          </a>
          <span className={`badge ${badgeType}`}>{badgeType}</span>
        </div>
        
        <a href={url} target="_blank" rel="noopener noreferrer" className="result-url">
          {url}
        </a>
      </div>

      {/* Visual Ranking Section */}
      <div className="ranking-container">
        <div className="relevance-bar-wrapper">
          <span className="relevance-label">Relevance</span>
          <div className="progress-track single-track">
            <div 
              className="progress-fill primary" 
              style={{ width: `${relevancePct}%` }}
            ></div>
          </div>
        </div>

        {/* Textual Stats Row */}
        {stats.length > 0 && (
          <div className="stats-text-row">
            {stats.map((stat, index) => (
              <React.Fragment key={stat.label}>
                <span>{stat.label}: <strong>{stat.value}</strong></span>
                {index < stats.length - 1 && <span className="divider">|</span>}
              </React.Fragment>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ResultItem;