import React, { useState } from 'react';

function ContentPreview({ content, wordCount }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  if (!content) {
    return (
      <div className="text-center py-8 text-gray-500">
        No content available
      </div>
    );
  }

  const previewLength = 1000;
  const shouldTruncate = content.length > previewLength;
  const displayContent = isExpanded ? content : content.slice(0, previewLength);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="text-sm text-gray-500">
          <span className="font-medium">{wordCount.toLocaleString()}</span> words
          {' | '}
          <span className="font-medium">{content.length.toLocaleString()}</span> characters
        </div>
        <button
          onClick={handleCopy}
          className="flex items-center text-sm text-gray-500 hover:text-blue-500 transition-colors"
        >
          {copied ? (
            <>
              <svg className="w-4 h-4 mr-1 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Copied!
            </>
          ) : (
            <>
              <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              Copy
            </>
          )}
        </button>
      </div>

      {/* Content */}
      <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
        <p className="whitespace-pre-wrap text-sm text-gray-700 leading-relaxed">
          {displayContent}
          {shouldTruncate && !isExpanded && '...'}
        </p>
      </div>

      {/* Expand/Collapse */}
      {shouldTruncate && (
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="mt-3 text-sm text-blue-500 hover:text-blue-600 font-medium flex items-center"
        >
          {isExpanded ? (
            <>
              <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
              </svg>
              Show less
            </>
          ) : (
            <>
              <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
              Show full content ({(content.length - previewLength).toLocaleString()} more characters)
            </>
          )}
        </button>
      )}
    </div>
  );
}

export default ContentPreview;
