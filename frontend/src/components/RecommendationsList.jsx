import React from 'react';

function RecommendationsList({ recommendations }) {
  if (!recommendations || recommendations.length === 0) {
    return (
      <div className="text-center py-8">
        <svg className="w-12 h-12 text-gray-300 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
        </svg>
        <p className="text-gray-500">No related news articles found</p>
        <p className="text-sm text-gray-400 mt-1">
          Try different content or add more articles to your database
        </p>
      </div>
    );
  }

  const getScoreColor = (score) => {
    if (score >= 0.7) return 'bg-green-100 text-green-700';
    if (score >= 0.4) return 'bg-yellow-100 text-yellow-700';
    return 'bg-gray-100 text-gray-700';
  };

  const getScoreBarWidth = (score) => {
    return `${score * 100}%`;
  };

  return (
    <div className="space-y-4">
      {recommendations.map((rec, index) => (
        <div
          key={rec.id}
          className="border rounded-lg p-4 hover:shadow-md transition-shadow bg-white"
        >
          <div className="flex items-start justify-between mb-2">
            <div className="flex items-center">
              <span className="text-xs font-medium text-gray-400 mr-2">
                #{index + 1}
              </span>
              <h3 className="font-semibold text-gray-900 line-clamp-2">
                {rec.title}
              </h3>
            </div>
            <span className={`ml-3 px-2 py-1 rounded text-xs font-medium whitespace-nowrap ${getScoreColor(rec.relevance_score)}`}>
              {(rec.relevance_score * 100).toFixed(0)}% match
            </span>
          </div>

          {/* Relevance Score Bar */}
          <div className="h-1 bg-gray-100 rounded-full mb-3 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-400 to-blue-600 rounded-full transition-all duration-500"
              style={{ width: getScoreBarWidth(rec.relevance_score) }}
            ></div>
          </div>

          <p className="text-sm text-gray-600 mb-3 line-clamp-2">
            {rec.summary}
          </p>

          {/* Matched Keywords */}
          {rec.matched_keywords && rec.matched_keywords.length > 0 && (
            <div className="mb-3">
              <p className="text-xs text-gray-400 mb-1">Matched keywords:</p>
              <div className="flex flex-wrap gap-1">
                {rec.matched_keywords.map((kw, i) => (
                  <span
                    key={i}
                    className="text-xs bg-blue-50 text-blue-600 px-2 py-0.5 rounded"
                  >
                    {kw}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Footer */}
          <div className="flex items-center justify-between pt-3 border-t">
            <div className="text-xs text-gray-400">
              {rec.published_date && (
                <span>
                  Published: {new Date(rec.published_date).toLocaleDateString()}
                </span>
              )}
            </div>
            {rec.url && (
              <a
                href={rec.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-blue-500 hover:text-blue-600 font-medium flex items-center"
              >
                Read article
                <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

export default RecommendationsList;
