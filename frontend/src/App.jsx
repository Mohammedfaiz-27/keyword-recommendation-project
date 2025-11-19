import React, { useState } from 'react';
import Header from './components/Header';
import InputSection from './components/InputSection';
import ResultsSection from './components/ResultsSection';
import { extractFromPDF, extractFromURL, extractPDFLinks } from './services/api';

function App() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [processingTime, setProcessingTime] = useState(null);
  const [linkResults, setLinkResults] = useState(null); // For PDF link extraction results

  const handleExtract = async (inputType, data, maxKeywords) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setLinkResults(null);

    try {
      let response;
      if (inputType === 'url') {
        response = await extractFromURL(data, maxKeywords);
        setResult(response.data);
        setProcessingTime(response.processing_time_ms);
      } else {
        // Use the NEW pdf-links endpoint that scrapes webpages
        response = await extractPDFLinks(data, {
          maxKeywordsPerLink: maxKeywords,
          maxNewsPerLink: 10,
          minRelevanceScore: 0.3,
          crawlTimeout: 15
        });

        // Store the link extraction results
        setLinkResults(response);
        setProcessingTime(response.processing_time_ms);

        // Also create a compatible result format for existing ResultsSection
        if (response.results && response.results.length > 0) {
          // Combine all keywords, entities, and recommendations from all scraped pages
          const allKeywords = [];
          const allRecommendations = [];
          const allEntities = {
            persons: [],
            locations: [],
            organizations: [],
            dates: [],
            misc: []
          };

          response.results.forEach((linkResult, linkIndex) => {
            if (linkResult.crawl_success) {
              linkResult.keywords.forEach(kw => {
                allKeywords.push({
                  keyword: kw.keyword,
                  score: kw.score,
                  type: kw.type
                });
              });

              // Aggregate entities from each page
              if (linkResult.entities) {
                if (linkResult.entities.persons) {
                  allEntities.persons.push(...linkResult.entities.persons);
                }
                if (linkResult.entities.locations) {
                  allEntities.locations.push(...linkResult.entities.locations);
                }
                if (linkResult.entities.organizations) {
                  allEntities.organizations.push(...linkResult.entities.organizations);
                }
                if (linkResult.entities.dates) {
                  allEntities.dates.push(...linkResult.entities.dates);
                }
                if (linkResult.entities.misc) {
                  allEntities.misc.push(...linkResult.entities.misc);
                }
              }

              linkResult.related_news.forEach((news, newsIndex) => {
                // Map the field names to match what RecommendationsList expects
                allRecommendations.push({
                  id: `${linkIndex}-${newsIndex}`,
                  title: news.title || `Article from ${news.source}`,
                  summary: news.content_preview || 'No summary available',
                  relevance_score: news.relevance_score,
                  matched_keywords: news.matched_keywords || [],
                  published_date: news.published_at,
                  url: news.url,
                  source: news.source
                });
              });
            }
          });

          // Remove duplicates from entities
          const uniqueEntities = {
            persons: [...new Set(allEntities.persons)],
            locations: [...new Set(allEntities.locations)],
            organizations: [...new Set(allEntities.organizations)],
            dates: [...new Set(allEntities.dates)],
            misc: [...new Set(allEntities.misc)]
          };

          // Create result in the format expected by ResultsSection
          setResult({
            content: response.results.map(r => r.scraped_content_preview).join('\n\n'),
            word_count: response.results.reduce((sum, r) => sum + r.word_count, 0),
            keywords: allKeywords,
            entities: uniqueEntities,
            recommendations: allRecommendations
          });
        }
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setResult(null);
    setError(null);
    setProcessingTime(null);
    setLinkResults(null);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Header />

      <main className="container mx-auto px-4 py-8 max-w-6xl">
        <InputSection
          onExtract={handleExtract}
          loading={loading}
          onClear={handleClear}
          hasResult={!!result}
        />

        {error && (
          <div className="mt-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
            <div className="flex items-center">
              <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <span className="font-medium">Error:</span>
              <span className="ml-1">{error}</span>
            </div>
          </div>
        )}

        {result && (
          <ResultsSection
            result={result}
            processingTime={processingTime}
          />
        )}
      </main>

      <footer className="bg-white border-t mt-12 py-6">
        <div className="container mx-auto px-4 text-center text-gray-500 text-sm">
          Keyword Recommendation System - Extract, Analyze, Discover
        </div>
      </footer>
    </div>
  );
}

export default App;
