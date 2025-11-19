"""
PDF Link Extraction Service

Extracts hyperlinks from PDFs using multiple methods:
1. PDF annotations (clickable links)
2. Regex pattern matching (plain text URLs)
3. Named anchor extraction
"""

import re
import logging
from typing import List, Set
from urllib.parse import urlparse
from io import BytesIO

import pdfplumber
from PyPDF2 import PdfReader

logger = logging.getLogger(__name__)


class LinkExtractor:
    """Extract hyperlinks from PDF documents."""

    # URL pattern for regex extraction
    URL_PATTERN = re.compile(
        r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[^\s\)\]\>\"\'\,]*',
        re.IGNORECASE
    )

    # Additional patterns for common URL formats
    WWW_PATTERN = re.compile(
        r'www\.[-\w.]+\.[-\w]+[^\s\)\]\>\"\'\,]*',
        re.IGNORECASE
    )

    # Domains to exclude (common non-article links)
    EXCLUDED_DOMAINS = {
        'facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com',
        'youtube.com', 'tiktok.com', 'pinterest.com', 'reddit.com',
        'fonts.googleapis.com', 'fonts.gstatic.com', 'cdn.', 'static.',
        'ads.', 'analytics.', 'tracking.', 'pixel.', 'beacon.',
        'doubleclick.net', 'googleadservices.com', 'googlesyndication.com'
    }

    # File extensions to exclude
    EXCLUDED_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.ico',
        '.css', '.js', '.woff', '.woff2', '.ttf', '.eot',
        '.pdf', '.zip', '.rar', '.exe', '.dmg', '.mp3', '.mp4', '.avi'
    }

    def __init__(self):
        self.extracted_links: Set[str] = set()

    async def extract_links(self, pdf_content: bytes) -> List[str]:
        """
        Extract all unique links from a PDF document.

        Args:
            pdf_content: Raw PDF file bytes

        Returns:
            List of unique, validated URLs
        """
        self.extracted_links = set()

        # Method 1: Extract from PDF annotations (clickable links)
        annotation_links = await self._extract_from_annotations(pdf_content)
        self.extracted_links.update(annotation_links)
        logger.info(f"Extracted {len(annotation_links)} links from annotations")

        # Method 2: Extract from text using regex
        text_links = await self._extract_from_text(pdf_content)
        self.extracted_links.update(text_links)
        logger.info(f"Extracted {len(text_links)} links from text")

        # Filter and validate links
        valid_links = self._filter_and_validate_links(list(self.extracted_links))
        logger.info(f"Total valid links after filtering: {len(valid_links)}")

        return valid_links

    async def _extract_from_annotations(self, pdf_content: bytes) -> Set[str]:
        """
        Extract links from PDF annotations using pdfplumber.
        These are clickable hyperlinks embedded in the PDF.
        """
        links = set()

        try:
            with pdfplumber.open(BytesIO(pdf_content)) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        # Get hyperlinks from page annotations
                        if page.annots:
                            for annot in page.annots:
                                if annot.get('uri'):
                                    uri = annot['uri']
                                    if isinstance(uri, str):
                                        links.add(uri.strip())

                        # Also check for link annotations in different format
                        if hasattr(page, 'hyperlinks'):
                            for link in page.hyperlinks:
                                if 'uri' in link:
                                    links.add(link['uri'].strip())

                    except Exception as e:
                        logger.warning(f"Error processing page {page_num} annotations: {e}")
                        continue

        except Exception as e:
            logger.error(f"pdfplumber annotation extraction failed: {e}")
            # Fallback to PyPDF2
            links.update(await self._extract_annotations_pypdf2(pdf_content))

        return links

    async def _extract_annotations_pypdf2(self, pdf_content: bytes) -> Set[str]:
        """Fallback annotation extraction using PyPDF2."""
        links = set()

        try:
            reader = PdfReader(BytesIO(pdf_content))

            for page_num, page in enumerate(reader.pages, 1):
                try:
                    if '/Annots' in page:
                        annotations = page['/Annots']
                        for annot in annotations:
                            annot_obj = annot.get_object()
                            if annot_obj.get('/Subtype') == '/Link':
                                if '/A' in annot_obj:
                                    action = annot_obj['/A']
                                    if '/URI' in action:
                                        uri = action['/URI']
                                        if isinstance(uri, str):
                                            links.add(uri.strip())
                except Exception as e:
                    logger.warning(f"Error processing PyPDF2 page {page_num}: {e}")
                    continue

        except Exception as e:
            logger.error(f"PyPDF2 annotation extraction failed: {e}")

        return links

    async def _extract_from_text(self, pdf_content: bytes) -> Set[str]:
        """
        Extract URLs from PDF text content using regex.
        Catches URLs that aren't clickable links.
        """
        links = set()

        try:
            with pdfplumber.open(BytesIO(pdf_content)) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        text = page.extract_text() or ""

                        # Find http/https URLs
                        http_urls = self.URL_PATTERN.findall(text)
                        links.update(http_urls)

                        # Find www URLs and convert to https
                        www_urls = self.WWW_PATTERN.findall(text)
                        for url in www_urls:
                            if not url.startswith('http'):
                                links.add(f"https://{url}")
                            else:
                                links.add(url)

                    except Exception as e:
                        logger.warning(f"Error extracting text from page {page_num}: {e}")
                        continue

        except Exception as e:
            logger.error(f"Text extraction failed: {e}")

        return links

    def _filter_and_validate_links(self, links: List[str]) -> List[str]:
        """
        Filter and validate extracted links.

        Removes:
        - Duplicate URLs
        - Invalid URLs
        - Social media links
        - Asset files (images, css, js)
        - Tracking/analytics URLs
        """
        valid_links = []
        seen_normalized = set()

        for link in links:
            try:
                # Clean the URL
                link = self._clean_url(link)
                if not link:
                    continue

                # Parse URL
                parsed = urlparse(link)

                # Must have valid scheme and netloc
                if parsed.scheme not in ('http', 'https'):
                    continue
                if not parsed.netloc:
                    continue

                # Check for excluded domains
                domain = parsed.netloc.lower()
                if any(excluded in domain for excluded in self.EXCLUDED_DOMAINS):
                    continue

                # Check for excluded file extensions
                path_lower = parsed.path.lower()
                if any(path_lower.endswith(ext) for ext in self.EXCLUDED_EXTENSIONS):
                    continue

                # Normalize for deduplication
                normalized = f"{parsed.netloc}{parsed.path}".lower().rstrip('/')
                if normalized in seen_normalized:
                    continue
                seen_normalized.add(normalized)

                valid_links.append(link)

            except Exception as e:
                logger.debug(f"Invalid URL '{link}': {e}")
                continue

        return valid_links

    def _clean_url(self, url: str) -> str:
        """Clean and normalize a URL."""
        if not url:
            return ""

        # Strip whitespace and common trailing characters
        url = url.strip()

        # Remove trailing punctuation that might have been captured
        while url and url[-1] in '.,;:)\'"}>':
            url = url[:-1]

        return url

    def get_link_metadata(self, links: List[str]) -> List[dict]:
        """
        Get metadata for each link (domain, path, etc.).
        Useful for displaying to users.
        """
        metadata = []

        for link in links:
            try:
                parsed = urlparse(link)
                metadata.append({
                    'url': link,
                    'domain': parsed.netloc,
                    'path': parsed.path,
                    'is_secure': parsed.scheme == 'https'
                })
            except Exception:
                metadata.append({
                    'url': link,
                    'domain': 'unknown',
                    'path': '',
                    'is_secure': False
                })

        return metadata
