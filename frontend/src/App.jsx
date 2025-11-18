import React, { useState } from 'react';
import Header from './components/Header';
import InputSection from './components/InputSection';
import ResultsSection from './components/ResultsSection';
import { extractFromPDF, extractFromURL } from './services/api';

function App() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [processingTime, setProcessingTime] = useState(null);

  const handleExtract = async (inputType, data, maxKeywords) => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      let response;
      if (inputType === 'url') {
        response = await extractFromURL(data, maxKeywords);
      } else {
        response = await extractFromPDF(data, maxKeywords);
      }

      setResult(response.data);
      setProcessingTime(response.processing_time_ms);
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
