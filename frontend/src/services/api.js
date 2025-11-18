const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

/**
 * Extract content and keywords from a PDF file
 */
export const extractFromPDF = async (file, maxKeywords = 10) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('max_keywords', maxKeywords.toString());

  const response = await fetch(`${API_BASE_URL}/extract/pdf`, {
    method: 'POST',
    body: formData,
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || 'Failed to extract from PDF');
  }

  return data;
};

/**
 * Extract content and keywords from a URL
 */
export const extractFromURL = async (url, maxKeywords = 10) => {
  const response = await fetch(`${API_BASE_URL}/extract/url`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ url, max_keywords: maxKeywords }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || 'Failed to extract from URL');
  }

  return data;
};

/**
 * Get recommendations for given keywords
 */
export const getRecommendations = async (keywords, limit = 10, minScore = 0.3) => {
  const response = await fetch(`${API_BASE_URL}/recommend`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ keywords, limit, min_score: minScore }),
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || 'Failed to get recommendations');
  }

  return data;
};

/**
 * Check API health status
 */
export const checkHealth = async () => {
  const response = await fetch(`${API_BASE_URL}/health`);
  return response.json();
};
