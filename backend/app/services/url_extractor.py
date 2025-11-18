import httpx
from newspaper import Article
from bs4 import BeautifulSoup
from typing import Optional
from app.config import get_settings

settings = get_settings()


class URLExtractor:
    """Service for extracting article content from URLs."""

    def __init__(self):
        self.timeout = settings.REQUEST_TIMEOUT
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    async def extract(self, url: str) -> dict:
        """
        Extract article content from URL.
        Uses newspaper3k as primary, BeautifulSoup as fallback.
        """
        # Try newspaper3k first (best for news articles)
        result = await self._extract_with_newspaper(url)

        # Fallback to BeautifulSoup if newspaper fails
        if not result or len(result.get("text", "").strip()) < 100:
            result = await self._extract_with_beautifulsoup(url)

        if not result or len(result.get("text", "").strip()) < 50:
            raise ValueError(f"Could not extract content from URL: {url}")

        return result

    async def _extract_with_newspaper(self, url: str) -> Optional[dict]:
        """Extract using newspaper3k library."""
        try:
            article = Article(url)
            article.download()
            article.parse()

            return {
                "text": article.text,
                "title": article.title,
                "authors": article.authors,
                "publish_date": str(article.publish_date) if article.publish_date else None,
                "top_image": article.top_image,
            }
        except Exception as e:
            print(f"Newspaper extraction failed: {e}")
            return None

    async def _extract_with_beautifulsoup(self, url: str) -> Optional[dict]:
        """Extract using BeautifulSoup as fallback."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=self.headers, follow_redirects=True)
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Remove unwanted elements
            for element in soup.find_all([
                "script", "style", "nav", "header", "footer",
                "aside", "iframe", "noscript", "form"
            ]):
                element.decompose()

            # Remove common ad/sidebar classes
            ad_classes = [
                "ad", "ads", "advertisement", "sidebar", "menu",
                "nav", "navigation", "footer", "header", "social",
                "share", "related", "recommended", "sponsored"
            ]

            for cls in ad_classes:
                for element in soup.find_all(class_=lambda x: x and cls in x.lower()):
                    element.decompose()
                for element in soup.find_all(id=lambda x: x and cls in x.lower()):
                    element.decompose()

            # Try to find main content
            main_content = (
                soup.find("article") or
                soup.find("main") or
                soup.find(class_=lambda x: x and "content" in x.lower()) or
                soup.find(class_=lambda x: x and "article" in x.lower()) or
                soup.find("body")
            )

            if main_content:
                # Get text and clean it
                text = main_content.get_text(separator="\n", strip=True)
            else:
                text = soup.get_text(separator="\n", strip=True)

            # Get title
            title = ""
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text(strip=True)
            else:
                h1 = soup.find("h1")
                if h1:
                    title = h1.get_text(strip=True)

            return {
                "text": text,
                "title": title,
                "authors": [],
                "publish_date": None,
                "top_image": None,
            }
        except Exception as e:
            print(f"BeautifulSoup extraction failed: {e}")
            return None
