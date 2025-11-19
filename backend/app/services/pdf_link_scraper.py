"""
PDF Link Scraper Service

This service:
1. Extracts URLs from PDF documents
2. Actually VISITS each URL and scrapes the webpage content
3. Extracts keywords from the SCRAPED CONTENT (not the URL text)
4. Returns combined results
"""

import re
import logging
import asyncio
from typing import List, Dict, Set, Optional
from urllib.parse import urlparse
from io import BytesIO
from dataclasses import dataclass, field
from datetime import datetime

import httpx
import pdfplumber
from PyPDF2 import PdfReader
from newspaper import Article, ArticleException
from bs4 import BeautifulSoup, Comment

logger = logging.getLogger(__name__)


@dataclass
class ScrapedPage:
    """Result of scraping a single webpage."""
    url: str
    success: bool
    title: str = ""
    content: str = ""  # The actual scraped text content
    word_count: int = 0
    error_message: str = ""
    scrape_time_ms: int = 0


class PDFLinkScraper:
    """
    Complete service for extracting links from PDFs and scraping their content.
    """

    # URL patterns
    URL_PATTERN = re.compile(
        r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s\)\]\>\"\'\,]*',
        re.IGNORECASE
    )

    WWW_PATTERN = re.compile(
        r'www\.[-\w.]+\.[-\w]+[^\s\)\]\>\"\'\,]*',
        re.IGNORECASE
    )

    # Domains to skip
    SKIP_DOMAINS = {
        'facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com',
        'youtube.com', 'tiktok.com', 'pinterest.com', 'reddit.com',
        'fonts.googleapis.com', 'fonts.gstatic.com',
        'doubleclick.net', 'googleadservices.com', 'googlesyndication.com'
    }

    # File extensions to skip
    SKIP_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.ico',
        '.css', '.js', '.woff', '.woff2', '.ttf', '.eot',
        '.pdf', '.zip', '.rar', '.exe', '.dmg', '.mp3', '.mp4'
    }

    # User agent for requests
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    def __init__(self, timeout: int = 15, max_concurrent: int = 5):
        self.timeout = timeout
        self.max_concurrent = max_concurrent

    async def extract_and_scrape(self, pdf_content: bytes) -> tuple[List[str], List[ScrapedPage]]:
        """
        Main method: Extract links from PDF and scrape each webpage.

        Args:
            pdf_content: Raw PDF file bytes

        Returns:
            Tuple of (list of URLs found, list of ScrapedPage results)
        """
        # Step 1: Extract all URLs from PDF
        print("=" * 60)
        print("EXTRACTING URLs FROM PDF...")
        urls = await self._extract_urls_from_pdf(pdf_content)
        print(f"Extracted {len(urls)} URLs from PDF")
        logger.info(f"Extracted {len(urls)} URLs from PDF")

        for url in urls:
            print(f"  Found URL: {url}")
            logger.info(f"  Found URL: {url}")

        if not urls:
            print("No URLs found in PDF!")
            return [], []

        # Step 2: Scrape each URL
        print("=" * 60)
        print("SCRAPING WEBPAGES...")
        scraped_pages = await self._scrape_all_urls(urls)

        for page in scraped_pages:
            if page.success:
                print(f"SUCCESS: {page.url}")
                print(f"  Title: {page.title}")
                print(f"  Content: {len(page.content)} chars")
            else:
                print(f"FAILED: {page.url} - {page.error_message}")

        print("=" * 60)

        return urls, scraped_pages

    async def _extract_urls_from_pdf(self, pdf_content: bytes) -> List[str]:
        """Extract all unique, valid URLs from PDF."""
        urls: Set[str] = set()

        try:
            # Method 1: Extract from PDF annotations (clickable links)
            with pdfplumber.open(BytesIO(pdf_content)) as pdf:
                for page in pdf.pages:
                    # Get hyperlinks from annotations - these are the most reliable
                    if page.annots:
                        for annot in page.annots:
                            uri = annot.get('uri', '')
                            if uri and isinstance(uri, str):
                                # Clean up the URI
                                clean_uri = uri.strip().replace('\n', '').replace('\r', '').replace(' ', '')
                                urls.add(clean_uri)
                                logger.info(f"Found annotation link: {clean_uri}")

                    # Also extract URLs from text using regex
                    text = page.extract_text() or ""

                    # Remove line breaks that might split URLs
                    # Join lines that end with common URL patterns
                    text_joined = re.sub(r'-\n', '', text)  # Handle hyphenation
                    text_joined = re.sub(r'(\S+)\n(\S+)', r'\1\2', text_joined)  # Join split words

                    # Find http/https URLs
                    for url in self.URL_PATTERN.findall(text_joined):
                        urls.add(url)

                    # Find www URLs
                    for url in self.WWW_PATTERN.findall(text_joined):
                        if not url.startswith('http'):
                            urls.add(f"https://{url}")
                        else:
                            urls.add(url)

        except Exception as e:
            logger.error(f"pdfplumber extraction failed: {e}")
            # Fallback to PyPDF2
            try:
                reader = PdfReader(BytesIO(pdf_content))
                for page in reader.pages:
                    if '/Annots' in page:
                        for annot in page['/Annots']:
                            obj = annot.get_object()
                            if obj.get('/Subtype') == '/Link' and '/A' in obj:
                                uri = obj['/A'].get('/URI', '')
                                if uri:
                                    urls.add(str(uri).strip())
            except Exception as e2:
                logger.error(f"PyPDF2 extraction also failed: {e2}")

        # Filter and validate URLs
        valid_urls = []
        seen = set()

        for url in urls:
            url = self._clean_url(url)
            if not url:
                continue

            try:
                parsed = urlparse(url)

                # Must have valid scheme
                if parsed.scheme not in ('http', 'https'):
                    continue

                # Must have domain
                if not parsed.netloc:
                    continue

                # Skip unwanted domains
                domain = parsed.netloc.lower()
                if any(skip in domain for skip in self.SKIP_DOMAINS):
                    continue

                # Skip unwanted file types
                path = parsed.path.lower()
                if any(path.endswith(ext) for ext in self.SKIP_EXTENSIONS):
                    continue

                # Deduplicate
                normalized = f"{parsed.netloc}{parsed.path}".lower().rstrip('/')
                if normalized in seen:
                    continue
                seen.add(normalized)

                valid_urls.append(url)

            except Exception:
                continue

        return valid_urls

    def _clean_url(self, url: str) -> str:
        """Clean and normalize a URL."""
        if not url:
            return ""

        url = url.strip()

        # Remove trailing punctuation
        while url and url[-1] in '.,;:)\'"}>':
            url = url[:-1]

        return url

    async def _scrape_all_urls(self, urls: List[str]) -> List[ScrapedPage]:
        """Scrape all URLs concurrently with rate limiting."""
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def scrape_with_limit(url: str) -> ScrapedPage:
            async with semaphore:
                return await self._scrape_single_url(url)

        tasks = [scrape_with_limit(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to failed results
        scraped_pages = []
        for url, result in zip(urls, results):
            if isinstance(result, Exception):
                scraped_pages.append(ScrapedPage(
                    url=url,
                    success=False,
                    error_message=str(result)
                ))
            else:
                scraped_pages.append(result)

        return scraped_pages

    async def _scrape_single_url(self, url: str) -> ScrapedPage:
        """
        Actually visit and scrape a single URL.
        This is where the real webpage scraping happens!
        """
        start_time = asyncio.get_event_loop().time()

        try:
            # Step 1: Fetch the webpage HTML
            logger.info(f"Fetching: {url}")
            html = await self._fetch_webpage(url)

            if not html:
                return ScrapedPage(
                    url=url,
                    success=False,
                    error_message="Empty response from server"
                )

            logger.info(f"Fetched {len(html)} bytes from {url}")

            # Step 2: Extract the main article content
            title, content = await self._extract_article_content(url, html)

            if not content or len(content) < 100:
                return ScrapedPage(
                    url=url,
                    success=False,
                    error_message="Could not extract sufficient content from page"
                )

            # Step 3: Clean the content
            content = self._clean_content(content)
            word_count = len(content.split())

            # Calculate time
            end_time = asyncio.get_event_loop().time()
            scrape_time = int((end_time - start_time) * 1000)

            logger.info(f"Successfully scraped {url}: {word_count} words, title: {title[:50]}...")

            return ScrapedPage(
                url=url,
                success=True,
                title=title,
                content=content,
                word_count=word_count,
                scrape_time_ms=scrape_time
            )

        except asyncio.TimeoutError:
            return ScrapedPage(
                url=url,
                success=False,
                error_message=f"Timeout after {self.timeout}s"
            )
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return ScrapedPage(
                url=url,
                success=False,
                error_message=str(e)
            )

    async def _fetch_webpage(self, url: str) -> Optional[str]:
        """Fetch webpage HTML using httpx."""
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

    async def _extract_article_content(self, url: str, html: str) -> tuple[str, str]:
        """
        Extract main article content from HTML.
        Uses newspaper3k first, then BeautifulSoup as fallback.
        """
        title = ""
        content = ""

        # Try newspaper3k first (best for news articles)
        try:
            article = Article(url)
            article.set_html(html)
            article.parse()

            title = article.title or ""
            content = article.text or ""

            if content and len(content) > 200:
                return title, content

        except ArticleException as e:
            logger.debug(f"Newspaper3k failed for {url}: {e}")
        except Exception as e:
            logger.debug(f"Newspaper3k error for {url}: {e}")

        # Fallback to BeautifulSoup
        try:
            soup = BeautifulSoup(html, 'lxml')

            # Get title
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text(strip=True)

            # Remove unwanted elements
            for tag in ['script', 'style', 'noscript', 'iframe', 'nav',
                       'header', 'footer', 'aside', 'form', 'button']:
                for element in soup.find_all(tag):
                    element.decompose()

            # Remove elements with ad/social/nav classes
            noise_pattern = re.compile(
                r'ad|ads|advert|sponsor|social|share|comment|sidebar|'
                r'footer|header|nav|menu|related|newsletter|cookie|popup',
                re.IGNORECASE
            )

            for element in soup.find_all(True):
                classes = ' '.join(element.get('class', []))
                element_id = element.get('id', '')
                if noise_pattern.search(f"{classes} {element_id}"):
                    element.decompose()

            # Remove comments
            for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
                comment.extract()

            # Try to find main content
            content_selectors = [
                'article', 'main', '[role="main"]',
                '.post-content', '.article-content', '.entry-content',
                '.content', '#content', '.post', '.article'
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

        except Exception as e:
            logger.error(f"BeautifulSoup extraction failed for {url}: {e}")

        return title, content

    def _clean_content(self, text: str) -> str:
        """Clean extracted text content."""
        if not text:
            return ""

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove common boilerplate
        boilerplate = [
            r'cookie[s]?\s+(policy|notice|settings)',
            r'accept\s+(all\s+)?cookies?',
            r'privacy\s+policy',
            r'terms\s+(of\s+)?(service|use)',
            r'subscribe\s+to\s+newsletter',
            r'sign\s+up\s+for',
            r'follow\s+us\s+on',
            r'share\s+(this\s+)?(on|via)',
            r'read\s+more\s+articles?',
            r'related\s+(articles?|posts?)',
            r'advertisement',
            r'sponsored\s+content',
        ]

        for pattern in boilerplate:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        # Remove URLs that leaked through
        text = re.sub(r'https?://\S+', '', text)

        # Clean up whitespace again
        text = re.sub(r'\s+', ' ', text).strip()

        # Truncate if too long
        if len(text) > 50000:
            text = text[:50000]

        return text
