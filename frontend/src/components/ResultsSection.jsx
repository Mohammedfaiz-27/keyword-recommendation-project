import React, { useState } from 'react';
import KeywordsDisplay from './KeywordsDisplay';
import EntitiesDisplay from './EntitiesDisplay';
import RecommendationsList from './RecommendationsList';
import ContentPreview from './ContentPreview';

function ResultsSection({ result, processingTime }) {
  const [activeTab, setActiveTab] = useState('keywords');

  const tabs = [
    { id: 'keywords', label: 'Keywords', count: result.keywords?.length || 0 },
    { id: 'entities', label: 'Entities', count: getTotalEntities(result.entities) },
    { id: 'recommendations', label: 'Related News', count: result.recommendations?.length || 0 },
    { id: 'content', label: 'Content', count: result.word_count || 0 },
  ];

  function getTotalEntities(entities) {
    if (!entities) return 0;
    return (
      (entities.persons?.length || 0) +
      (entities.locations?.length || 0) +
      (entities.organizations?.length || 0)
    );
  }

  return (
    <div className="mt-8">
      {/* Stats Bar */}
      <div className="bg-white rounded-xl shadow-sm border p-4 mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-6">
            <div className="text-center">
              <p className="text-2xl font-bold text-blue-500">{result.keywords?.length || 0}</p>
              <p className="text-xs text-gray-500">Keywords</p>
            </div>
            <div className="h-8 w-px bg-gray-200"></div>
            <div className="text-center">
              <p className="text-2xl font-bold text-green-500">{result.recommendations?.length || 0}</p>
              <p className="text-xs text-gray-500">Matches</p>
            </div>
            <div className="h-8 w-px bg-gray-200"></div>
            <div className="text-center">
              <p className="text-2xl font-bold text-purple-500">{result.word_count || 0}</p>
              <p className="text-xs text-gray-500">Words</p>
            </div>
          </div>
          {processingTime && (
            <div className="text-sm text-gray-500">
              Processed in <span className="font-medium">{processingTime}ms</span>
            </div>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-xl shadow-sm border overflow-hidden">
        <div className="border-b">
          <div className="flex">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex-1 py-3 px-4 text-sm font-medium transition-colors relative ${
                  activeTab === tab.id
                    ? 'text-blue-500 bg-blue-50'
                    : 'text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                }`}
              >
                {tab.label}
                {tab.count > 0 && (
                  <span className={`ml-2 px-2 py-0.5 rounded-full text-xs ${
                    activeTab === tab.id
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-200 text-gray-600'
                  }`}>
                    {tab.count}
                  </span>
                )}
                {activeTab === tab.id && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-500"></div>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Tab Content */}
        <div className="p-6">
          {activeTab === 'keywords' && (
            <KeywordsDisplay keywords={result.keywords} />
          )}
          {activeTab === 'entities' && (
            <EntitiesDisplay entities={result.entities} />
          )}
          {activeTab === 'recommendations' && (
            <RecommendationsList recommendations={result.recommendations} />
          )}
          {activeTab === 'content' && (
            <ContentPreview content={result.content} wordCount={result.word_count} />
          )}
        </div>
      </div>
    </div>
  );
}

export default ResultsSection;
