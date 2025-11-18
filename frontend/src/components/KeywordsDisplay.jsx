import React from 'react';

function KeywordsDisplay({ keywords }) {
  if (!keywords || keywords.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No keywords extracted
      </div>
    );
  }

  const getTypeColor = (type) => {
    switch (type) {
      case 'entity':
        return 'bg-purple-100 text-purple-800 border-purple-200';
      case 'phrase':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getScoreColor = (score) => {
    if (score >= 0.8) return 'text-green-600';
    if (score >= 0.5) return 'text-yellow-600';
    return 'text-gray-500';
  };

  return (
    <div>
      <div className="mb-4">
        <h3 className="text-sm font-medium text-gray-500 mb-2">Keyword Types</h3>
        <div className="flex space-x-3 text-xs">
          <span className="flex items-center">
            <span className="w-3 h-3 rounded bg-purple-100 border border-purple-200 mr-1"></span>
            Entity
          </span>
          <span className="flex items-center">
            <span className="w-3 h-3 rounded bg-blue-100 border border-blue-200 mr-1"></span>
            Phrase
          </span>
          <span className="flex items-center">
            <span className="w-3 h-3 rounded bg-gray-100 border border-gray-200 mr-1"></span>
            Noun
          </span>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {keywords.map((kw, index) => (
          <div
            key={index}
            className={`inline-flex items-center px-3 py-2 rounded-lg border ${getTypeColor(kw.type)} transition-transform hover:scale-105`}
          >
            <span className="font-medium">{kw.keyword}</span>
            <span className={`ml-2 text-xs font-semibold ${getScoreColor(kw.score)}`}>
              {(kw.score * 100).toFixed(0)}%
            </span>
          </div>
        ))}
      </div>

      {/* Score Legend */}
      <div className="mt-6 pt-4 border-t">
        <h3 className="text-sm font-medium text-gray-500 mb-2">Score Legend</h3>
        <div className="flex space-x-4 text-xs">
          <span className="flex items-center">
            <span className="w-2 h-2 rounded-full bg-green-500 mr-1"></span>
            High (80%+)
          </span>
          <span className="flex items-center">
            <span className="w-2 h-2 rounded-full bg-yellow-500 mr-1"></span>
            Medium (50-79%)
          </span>
          <span className="flex items-center">
            <span className="w-2 h-2 rounded-full bg-gray-400 mr-1"></span>
            Low (&lt;50%)
          </span>
        </div>
      </div>
    </div>
  );
}

export default KeywordsDisplay;
