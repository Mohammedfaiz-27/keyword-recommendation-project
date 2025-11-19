"""
Webpage Crawler Service

Crawls webpages and extracts clean article content.
Handles async batch processing with timeout and error handling.
"""

import asyncio
import logging
import re
from typing import List, Optional
from dataclasses import dataclass, field
from datetime import datetime

import httpx
from newspaper import Article, ArticleException
from bs4 import BeautifulSoup, Comment

logger = logging.getLogger(__name__)


@dataclass
class CrawlResult:
    """Result of crawling a single webpage."""
    url: str
    success: bool
    title: str = ""
    content: str = ""
    authors: List[str] = field(default_factory=list)
    publish_date: Optional[datetime] = None
    error_message: str = ""
    crawl_time_ms: int = 0


class WebpageCrawler:
    """
    Async webpage crawler for extracting article content.

    Features:
    - Async batch processing
    - Multiple extraction methods
    - Aggressive content cleaning
    - Timeout and error handling
    """

    # Request configuration
    DEFAULT_TIMEOUT = 15  # seconds
    MAX_CONCURRENT_REQUESTS = 10

    # User agent to avoid blocks
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # Elements to remove for clean extraction
    REMOVE_TAGS = [
        'script', 'style', 'noscript', 'iframe', 'embed', 'object',
        'nav', 'header', 'footer', 'aside', 'form', 'button',
        'advertisement', 'ads', 'social', 'share', 'comment', 'comments',
        'sidebar', 'widget', 'popup', 'modal', 'cookie', 'newsletter',
        'subscription', 'promo', 'related', 'recommended'
    ]

    # Classes/IDs that typically contain noise
    NOISE_PATTERNS = [
        r'ad[-_]?', r'ads[-_]?', r'advert', r'sponsor', r'promo',
        r'social', r'share', r'comment', r'sidebar', r'widget',
        r'footer', r'header', r'nav', r'menu', r'breadcrumb',
        r'related', r'recommend', r'popular', r'trending',
        r'newsletter', r'subscribe', r'signup', r'cookie',
        r'popup', r'modal', r'overlay', r'banner'
    ]

    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.noise_regex = re.compile(
            '|'.join(self.NOISE_PATTERNS),
            re.IGNORECASE
        )

    async def crawl_urls(self, urls: List[str]) -> List[CrawlResult]:
        """
        Crawl multiple URLs concurrently.

        Args:
            urls: List of URLs to crawl

        Returns:
            List of CrawlResult objects
        """
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(self.MAX_CONCURRENT_REQUESTS)

        async def crawl_with_semaphore(url: str) -> CrawlResult:
            async with semaphore:
                return await self._crawl_single_url(url)

        # Crawl all URLs concurrently
        tasks = [crawl_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to failed results
        processed_results = []
        for url, result in zip(urls, results):
            if isinstance(result, Exception):
                processed_results.append(CrawlResult(
                    url=url,
                    success=False,
                    error_message=str(result)
                ))
            else:
                processed_results.append(result)

        return processed_results

    async def _crawl_single_url(self, url: str) -> CrawlResult:
        """Crawl a single URL with timeout handling."""
        start_time = asyncio.get_event_loop().time()

        try:
            # Fetch the page
            html_content = await self._fetch_page(url)
            if not html_content:
                return CrawlResult(
                    url=url,
                    success=False,
                    error_message="Empty response from server"
                )

            # Extract content using newspaper3k
            result = await self._extract_with_newspaper(url, html_content)

            # If newspaper fails or returns little content, use BeautifulSoup fallback
            if not result.success or len(result.content) < 200:
                soup_result = await self._extract_with_beautifulsoup(url, html_content)
                if soup_result.success and len(soup_result.content) > len(result.content):
                    result = soup_result

            # Calculate crawl time
            end_time = asyncio.get_event_loop().time()
            result.crawl_time_ms = int((end_time - start_time) * 1000)

            return result

        except asyncio.TimeoutError:
            return CrawlResult(
                url=url,
                success=False,
                error_message=f"Request timed out after {self.timeout}s"
            )
        except Exception as e:
            logger.error(f"Error crawling {url}: {e}")
            return CrawlResult(
                url=url,
                success=False,
                error_message=str(e)
            )

    async def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch webpage HTML with proper headers."""
        headers = {
            'User-Agent': self.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }

        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers=headers
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    async def _extract_with_newspaper(self, url: str, html: str) -> CrawlResult:
        """Extract article content using newspaper3k."""
        try:
            article = Article(url)
            article.set_html(html)
            article.parse()

            # Get clean text
            content = article.text or ""

            # Additional cleaning
            content = self._deep_clean_text(content)

            if not content or len(content) < 100:
                return CrawlResult(
                    url=url,
                    success=False,
                    error_message="Insufficient content extracted"
                )

            return CrawlResult(
                url=url,
                success=True,
                title=article.title or "",
                content=content,
                authors=article.authors or [],
                publish_date=article.publish_date
            )

        except ArticleException as e:
            return CrawlResult(
                url=url,
                success=False,
                error_message=f"Newspaper extraction failed: {e}"
            )
        except Exception as e:
            return CrawlResult(
                url=url,
                success=False,
                error_message=f"Unexpected error: {e}"
            )

    async def _extract_with_beautifulsoup(self, url: str, html: str) -> CrawlResult:
        """Fallback extraction using BeautifulSoup with aggressive cleaning."""
        try:
            soup = BeautifulSoup(html, 'lxml')

            # Get title
            title = ""
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True)

            # Remove unwanted elements
            for tag in self.REMOVE_TAGS:
                for element in soup.find_all(tag):
                    element.decompose()

            # Remove elements with noise class/id patterns
            for element in soup.find_all(True):
                element_classes = ' '.join(element.get('class', []))
                element_id = element.get('id', '')
                combined = f"{element_classes} {element_id}"

                if self.noise_regex.search(combined):
                    element.decompose()

            # Remove comments
            for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
                comment.extract()

            # Try to find main content area
            content = ""

            # Priority order for content containers
            content_selectors = [
                'article',
                '[role="main"]',
                'main',
                '.post-content',
                '.article-content',
                '.entry-content',
                '.content',
                '#content',
                '.post',
                '.article',
            ]

            for selector in content_selectors:
                container = soup.select_one(selector)
                if container:
                    content = container.get_text(separator=' ', strip=True)
                    if len(content) > 200:
                        break

            # Fallback to body
            if not content or len(content) < 200:
                body = soup.find('body')
                if body:
                    content = body.get_text(separator=' ', strip=True)

            # Deep clean the extracted text
            content = self._deep_clean_text(content)

            if not content or len(content) < 100:
                return CrawlResult(
                    url=url,
                    success=False,
                    error_message="Insufficient content after cleaning"
                )

            return CrawlResult(
                url=url,
                success=True,
                title=title,
                content=content
            )

        except Exception as e:
            return CrawlResult(
                url=url,
                success=False,
                error_message=f"BeautifulSoup extraction failed: {e}"
            )

    def _deep_clean_text(self, text: str) -> str:
        """
        Aggressively clean extracted text.

        Removes:
        - Excessive whitespace
        - Common boilerplate patterns
        - Navigation text
        - Cookie notices
        - Social sharing text
        """
        if not text:
            return ""

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove common boilerplate patterns
        boilerplate_patterns = [
            r'cookie[s]?\s+(policy|notice|settings|preferences)',
            r'accept\s+(all\s+)?cookies?',
            r'we\s+use\s+cookies?',
            r'privacy\s+policy',
            r'terms\s+(of\s+)?(service|use)',
            r'subscribe\s+(to\s+)?(our\s+)?newsletter',
            r'sign\s+up\s+for',
            r'follow\s+us\s+on',
            r'share\s+(this\s+)?(on|via)',
            r'(facebook|twitter|linkedin|instagram)\s+share',
            r'read\s+more\s+articles?',
            r'related\s+(articles?|posts?|stories)',
            r'you\s+may\s+(also\s+)?like',
            r'advertisement',
            r'sponsored\s+content',
            r'skip\s+to\s+(main\s+)?content',
            r'menu\s+toggle',
            r'search\s+toggle',
        ]

        for pattern in boilerplate_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        # Remove URLs that might have leaked through
        text = re.sub(r'https?://\S+', '', text)

        # Clean up resulting whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        # Truncate if too long (keep first 50000 chars)
        if len(text) > 50000:
            text = text[:50000]

        return text
