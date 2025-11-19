from rapidfuzz import fuzz, process
from bson import ObjectId
from datetime import datetime
from app.models.database import get_database
from app.models.schemas import NewsRecommendation, KeywordItem
from app.config import get_settings

settings = get_settings()


class Recommender:
    """
    Service for finding and ranking related news articles based on keywords.

    Searches across multiple collections in smart_radar database:
    - posts_table: Social media posts with key_narratives, post_text
    - raw_data: Raw API data with keyword field
    - print_daily: Daily print news with content
    - print_magazines: Magazine articles with content
    """

    def __init__(self):
        self.db = None
        self.fuzzy_threshold = settings.FUZZY_MATCH_THRESHOLD

    async def get_recommendations(
        self,
        keywords: list[KeywordItem],
        limit: int = 10,
        min_score: float = 0.3
    ) -> list[NewsRecommendation]:
        """
        Find and rank articles matching the given keywords across all collections.
        """
        self.db = get_database()

        if not keywords:
            return []

        # Extract keyword strings
        keyword_strings = [k.keyword.lower() for k in keywords]
        keyword_weights = {k.keyword.lower(): k.score for k in keywords}

        print(f"Searching for keywords: {keyword_strings}")

        # Find matching articles from all collections
        matched_articles = {}

        # Search posts_table
        posts_matches = await self._search_posts_table(keyword_strings)
        print(f"Found {len(posts_matches)} matches in posts_table")
        for article in posts_matches:
            article_id = str(article["_id"])
            matched_articles[article_id] = {
                "article": article,
                "source": "posts_table",
                "matched_keywords": set(),
                "match_scores": []
            }
            # Calculate matches
            self._calculate_matches(article, keyword_strings, keyword_weights, matched_articles[article_id])

        # Search raw_data
        raw_matches = await self._search_raw_data(keyword_strings)
        print(f"Found {len(raw_matches)} matches in raw_data")
        for article in raw_matches:
            article_id = str(article["_id"])
            if article_id not in matched_articles:
                matched_articles[article_id] = {
                    "article": article,
                    "source": "raw_data",
                    "matched_keywords": set(),
                    "match_scores": []
                }
            self._calculate_matches(article, keyword_strings, keyword_weights, matched_articles[article_id])

        # Search print_daily
        print_matches = await self._search_print_daily(keyword_strings)
        print(f"Found {len(print_matches)} matches in print_daily")
        for article in print_matches:
            article_id = str(article["_id"])
            if article_id not in matched_articles:
                matched_articles[article_id] = {
                    "article": article,
                    "source": "print_daily",
                    "matched_keywords": set(),
                    "match_scores": []
                }
            self._calculate_matches(article, keyword_strings, keyword_weights, matched_articles[article_id])

        # Search print_magazines
        mag_matches = await self._search_print_magazines(keyword_strings)
        print(f"Found {len(mag_matches)} matches in print_magazines")
        for article in mag_matches:
            article_id = str(article["_id"])
            if article_id not in matched_articles:
                matched_articles[article_id] = {
                    "article": article,
                    "source": "print_magazines",
                    "matched_keywords": set(),
                    "match_scores": []
                }
            self._calculate_matches(article, keyword_strings, keyword_weights, matched_articles[article_id])

        # Calculate final relevance scores and create recommendations
        recommendations = []
        for article_id, data in matched_articles.items():
            if not data["match_scores"]:
                continue

            # Calculate relevance score
            sorted_scores = sorted(data["match_scores"], reverse=True)
            relevance = 0
            for i, score in enumerate(sorted_scores):
                relevance += score * (0.8 ** i)
            relevance = min(relevance, 1.0)

            if relevance >= min_score:
                article = data["article"]
                source = data["source"]

                # Extract fields based on source collection
                title, summary, url, pub_date = self._extract_fields(article, source)

                recommendations.append(NewsRecommendation(
                    id=article_id,
                    title=title,
                    summary=summary,
                    url=url,
                    published_date=pub_date,
                    relevance_score=round(relevance, 2),
                    matched_keywords=list(data["matched_keywords"])
                ))

        # Sort by relevance and return top N
        recommendations.sort(key=lambda x: x.relevance_score, reverse=True)
        print(f"Returning {len(recommendations[:limit])} recommendations")
        return recommendations[:limit]

    def _calculate_matches(self, article: dict, keyword_strings: list, keyword_weights: dict, match_data: dict):
        """Calculate keyword matches for an article."""
        # Get searchable text from article
        searchable_texts = []

        # posts_table fields
        if "post_text" in article:
            searchable_texts.append(str(article["post_text"]).lower())
        if "key_narratives" in article and article["key_narratives"]:
            if isinstance(article["key_narratives"], list):
                searchable_texts.extend([str(n).lower() for n in article["key_narratives"]])
            else:
                searchable_texts.append(str(article["key_narratives"]).lower())

        # raw_data fields
        if "keyword" in article:
            searchable_texts.append(str(article["keyword"]).lower())

        # print_daily/print_magazines fields
        if "content" in article:
            searchable_texts.append(str(article["content"]).lower())
        if "matched_clusters" in article and article["matched_clusters"]:
            if isinstance(article["matched_clusters"], list):
                searchable_texts.extend([str(c).lower() for c in article["matched_clusters"]])
        if "intelligence" in article:
            searchable_texts.append(str(article["intelligence"]).lower())

        # Join all searchable text
        full_text = " ".join(searchable_texts)

        # Check each keyword
        for kw in keyword_strings:
            # Exact match
            if kw in full_text:
                match_data["matched_keywords"].add(kw)
                match_data["match_scores"].append(keyword_weights.get(kw, 0.5) * 1.0)
            else:
                # Fuzzy match
                for text in searchable_texts:
                    if text:
                        similarity = fuzz.partial_ratio(kw, text) / 100
                        if similarity >= self.fuzzy_threshold:
                            match_data["matched_keywords"].add(kw)
                            match_data["match_scores"].append(keyword_weights.get(kw, 0.5) * similarity * 0.8)
                            break

    def _extract_fields(self, article: dict, source: str) -> tuple:
        """Extract title, summary, url, and date based on source collection."""
        title = "Untitled"
        summary = "No summary available"
        url = None
        pub_date = None

        if source == "posts_table":
            # Use author_username or platform as title
            title = f"Post by @{article.get('author_username', 'Unknown')}"
            if article.get('platform'):
                title += f" on {article['platform']}"

            # Use post_text as summary
            post_text = article.get('post_text', '')
            if post_text:
                summary = post_text[:300] + "..." if len(post_text) > 300 else post_text

            url = article.get('post_url')
            pub_date = article.get('posted_at') or article.get('created_at')

        elif source == "raw_data":
            # Use keyword and platform as title
            keyword = article.get('keyword', 'Unknown')
            platform = article.get('platform', '')
            title = f"{keyword} ({platform})" if platform else keyword

            # Use api_endpoint or keyword as summary
            summary = f"Data from {article.get('api_endpoint', 'API')} - Keyword: {keyword}"
            pub_date = article.get('fetched_at') or article.get('created_at')

        elif source in ["print_daily", "print_magazines"]:
            # Use publisher as title
            publisher = article.get('publisher', 'Unknown Publisher')
            platform = article.get('platform', '')
            title = f"{publisher}" if publisher != 'Unknown Publisher' else f"Article from {platform}"

            # Use content as summary
            content = article.get('content', '')
            if content:
                summary = content[:300] + "..." if len(content) > 300 else content

            pub_date = article.get('published_at') or article.get('collected_at')

        # Format date
        if pub_date:
            if isinstance(pub_date, datetime):
                pub_date = pub_date.strftime("%Y-%m-%d")
            else:
                pub_date = str(pub_date)[:10]

        return title, summary, url, pub_date

    async def _search_posts_table(self, keywords: list[str]) -> list[dict]:
        """Search posts_table collection."""
        collection = self.db["posts_table"]

        try:
            # Use proper regex pattern - join keywords with OR
            pattern = "|".join([kw.replace(".", r"\.") for kw in keywords])

            cursor = collection.find({
                "$or": [
                    {"post_text": {"$regex": pattern, "$options": "i"}},
                    {"key_narratives": {"$regex": pattern, "$options": "i"}},
                ]
            }).limit(50)

            return await cursor.to_list(length=50)
        except Exception as e:
            print(f"Error searching posts_table: {e}")
            # Fallback: get all and filter
            try:
                cursor = collection.find({}).limit(100)
                all_posts = await cursor.to_list(length=100)
                return [p for p in all_posts if self._text_contains_keywords(p, keywords)]
            except:
                return []

    async def _search_raw_data(self, keywords: list[str]) -> list[dict]:
        """Search raw_data collection by keyword field."""
        collection = self.db["raw_data"]

        try:
            # Search in keyword field
            cursor = collection.find({
                "$or": [
                    {"keyword": {"$regex": "|".join(keywords), "$options": "i"}},
                ]
            }).limit(50)

            return await cursor.to_list(length=50)
        except Exception as e:
            print(f"Error searching raw_data: {e}")
            return []

    async def _search_print_daily(self, keywords: list[str]) -> list[dict]:
        """Search print_daily collection."""
        collection = self.db["print_daily"]

        try:
            cursor = collection.find({
                "$or": [
                    {"content": {"$regex": "|".join(keywords), "$options": "i"}},
                    {"intelligence": {"$regex": "|".join(keywords), "$options": "i"}},
                ]
            }).limit(20)

            return await cursor.to_list(length=20)
        except Exception as e:
            print(f"Error searching print_daily: {e}")
            # Fallback
            try:
                cursor = collection.find({}).limit(20)
                all_docs = await cursor.to_list(length=20)
                return [d for d in all_docs if self._text_contains_keywords(d, keywords)]
            except:
                return []

    async def _search_print_magazines(self, keywords: list[str]) -> list[dict]:
        """Search print_magazines collection."""
        collection = self.db["print_magazines"]

        try:
            cursor = collection.find({
                "$or": [
                    {"content": {"$regex": "|".join(keywords), "$options": "i"}},
                    {"intelligence": {"$regex": "|".join(keywords), "$options": "i"}},
                ]
            }).limit(20)

            return await cursor.to_list(length=20)
        except Exception as e:
            print(f"Error searching print_magazines: {e}")
            try:
                cursor = collection.find({}).limit(20)
                all_docs = await cursor.to_list(length=20)
                return [d for d in all_docs if self._text_contains_keywords(d, keywords)]
            except:
                return []

    def _text_contains_keywords(self, doc: dict, keywords: list[str]) -> bool:
        """Check if document contains any of the keywords."""
        # Combine all text fields
        text_fields = ['post_text', 'content', 'keyword', 'key_narratives', 'intelligence']
        full_text = ""

        for field in text_fields:
            if field in doc:
                value = doc[field]
                if isinstance(value, list):
                    full_text += " ".join([str(v) for v in value])
                else:
                    full_text += str(value)

        full_text = full_text.lower()

        for kw in keywords:
            if kw.lower() in full_text:
                return True

        return False

    async def log_extraction(self, log_data: dict):
        """Log extraction request to database."""
        self.db = get_database()
        try:
            await self.db.extraction_logs.insert_one(log_data)
        except Exception as e:
            print(f"Failed to log extraction: {e}")
