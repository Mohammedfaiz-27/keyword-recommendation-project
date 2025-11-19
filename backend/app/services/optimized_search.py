"""
Optimized Database Search Service

Features:
- Batch queries for multiple keyword sets
- Regex partial matching
- Optional fuzzy matching
- Query result caching
- Relevance scoring
"""

import re
import logging
from typing import List, Dict, Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


class OptimizedSearchService:
    """
    Optimized news article search with batch processing and caching.
    """

    # Collections to search
    SEARCH_COLLECTIONS = [
        'posts_table',
        'raw_data',
        'print_daily',
        'print_magazines',
        'news_articles'
    ]

    # Field mappings for different collections
    COLLECTION_FIELDS = {
        'posts_table': {
            'text_field': 'post_text',
            'keyword_field': 'key_narratives',
            'title_field': None,
            'date_field': 'posted_at',
            'url_field': 'post_url'
        },
        'raw_data': {
            'text_field': 'keyword',
            'keyword_field': 'keyword',
            'title_field': None,
            'date_field': 'fetched_at',
            'url_field': None
        },
        'print_daily': {
            'text_field': 'content',
            'keyword_field': 'intelligence',
            'title_field': None,
            'date_field': 'published_at',
            'url_field': None
        },
        'print_magazines': {
            'text_field': 'content',
            'keyword_field': 'intelligence',
            'title_field': None,
            'date_field': 'published_at',
            'url_field': None
        },
        'news_articles': {
            'text_field': 'content',
            'keyword_field': 'keywords',
            'title_field': 'title',
            'date_field': 'published_date',
            'url_field': 'url'
        }
    }

    def __init__(
        self,
        db: AsyncIOMotorDatabase,
        fuzzy_threshold: float = 0.6,
        enable_fuzzy: bool = True
    ):
        self.db = db
        self.fuzzy_threshold = fuzzy_threshold
        self.enable_fuzzy = enable_fuzzy
        self._cache: Dict[str, List[Dict]] = {}

    async def search_for_keywords_batch(
        self,
        keyword_sets: List[List[Dict]],
        limit_per_set: int = 10,
        min_score: float = 0.3
    ) -> List[List[Dict]]:
        """
        Search for news articles matching multiple keyword sets.
        Optimized for batch processing.

        Args:
            keyword_sets: List of keyword lists (one per source link)
            limit_per_set: Max results per keyword set
            min_score: Minimum relevance score

        Returns:
            List of result lists, one per keyword set
        """
        results = []

        # Collect all unique keywords for batch query
        all_keywords = set()
        for kw_list in keyword_sets:
            for kw_dict in kw_list:
                all_keywords.add(kw_dict['keyword'].lower())

        print(f"Searching database with {len(all_keywords)} keywords:")
        print(f"  Keywords: {list(all_keywords)[:10]}...")  # Show first 10

        # Pre-fetch all potential matches in one batch
        all_matches = await self._batch_fetch_matches(list(all_keywords))
        print(f"  Found {len(all_matches)} total matches from database")

        # Now filter and score for each keyword set
        for kw_list in keyword_sets:
            keywords = [kw['keyword'].lower() for kw in kw_list]
            keyword_scores = {kw['keyword'].lower(): kw['score'] for kw in kw_list}

            # Score each match
            scored_results = []
            seen_ids = set()

            for match in all_matches:
                match_id = str(match.get('_id', ''))
                if match_id in seen_ids:
                    continue

                # Calculate relevance score
                relevance = self._calculate_relevance(
                    match,
                    keywords,
                    keyword_scores
                )

                if relevance >= min_score:
                    scored_results.append({
                        **match,
                        'relevance_score': round(relevance, 3)
                    })
                    seen_ids.add(match_id)

            # Sort by relevance and limit
            scored_results.sort(key=lambda x: x['relevance_score'], reverse=True)
            results.append(scored_results[:limit_per_set])

            print(f"  After scoring: {len(scored_results)} results passed min_score of {min_score}")
            if scored_results:
                print(f"    Top score: {scored_results[0]['relevance_score']}")
            else:
                print(f"    No results passed the minimum score threshold!")

        return results

    async def _batch_fetch_matches(
        self,
        keywords: List[str]
    ) -> List[Dict]:
        """
        Fetch all potential matches for a set of keywords in batch.
        Uses $or with regex for partial matching.
        """
        if not keywords:
            return []

        all_matches = []

        for collection_name in self.SEARCH_COLLECTIONS:
            try:
                collection = self.db[collection_name]
                fields = self.COLLECTION_FIELDS.get(collection_name, {})

                # Build query with $or for all keywords
                text_field = fields.get('text_field', 'content')
                keyword_field = fields.get('keyword_field', 'keywords')

                # Create $or conditions for each keyword using string regex
                or_conditions = []
                for kw in keywords:
                    # Escape special regex characters and use string pattern
                    escaped = re.escape(kw)
                    or_conditions.extend([
                        {text_field: {'$regex': escaped, '$options': 'i'}},
                        {keyword_field: {'$regex': escaped, '$options': 'i'}}
                    ])

                if not or_conditions:
                    continue

                query = {'$or': or_conditions}

                # Execute query with limit
                cursor = collection.find(query).limit(500)

                count_before = len(all_matches)
                async for doc in cursor:
                    # Add source collection info
                    doc['_source_collection'] = collection_name
                    doc['_id'] = str(doc['_id'])
                    all_matches.append(doc)

                count_after = len(all_matches)
                print(f"  {collection_name}: found {count_after - count_before} matches")

            except Exception as e:
                print(f"  Error searching {collection_name}: {e}")
                logger.error(f"Error searching {collection_name}: {e}")
                continue

        return all_matches

    async def search_for_keywords(
        self,
        keywords: List[Dict],
        limit: int = 10,
        min_score: float = 0.3
    ) -> List[Dict]:
        """
        Search for a single keyword set.
        Wrapper around batch search for backward compatibility.
        """
        results = await self.search_for_keywords_batch(
            [keywords],
            limit_per_set=limit,
            min_score=min_score
        )
        return results[0] if results else []

    def _calculate_relevance(
        self,
        document: Dict,
        keywords: List[str],
        keyword_scores: Dict[str, float]
    ) -> float:
        """
        Calculate relevance score for a document.

        Scoring factors:
        - Exact keyword matches (weighted by keyword importance)
        - Partial/fuzzy matches
        - Number of matching keywords
        """
        total_score = 0.0
        matches = 0

        # Get document text
        fields = self.COLLECTION_FIELDS.get(
            document.get('_source_collection', ''),
            {}
        )

        text_content = str(document.get(fields.get('text_field', 'content'), ''))
        keyword_content = document.get(fields.get('keyword_field', 'keywords'), '')

        # Handle different keyword formats
        if isinstance(keyword_content, list):
            keyword_content = ' '.join(str(k) for k in keyword_content)
        else:
            keyword_content = str(keyword_content)

        combined_text = f"{text_content} {keyword_content}".lower()

        for keyword in keywords:
            kw_lower = keyword.lower()
            kw_weight = keyword_scores.get(kw_lower, 0.5)

            # Check for exact match
            if kw_lower in combined_text:
                # Count occurrences
                count = combined_text.count(kw_lower)
                score = min(count * 0.3, 1.0) * kw_weight
                total_score += score
                matches += 1

            # Optional fuzzy matching
            elif self.enable_fuzzy:
                # Check fuzzy match against significant words
                words = combined_text.split()
                for word in words:
                    if len(word) >= 3:
                        similarity = fuzz.ratio(kw_lower, word) / 100
                        if similarity >= self.fuzzy_threshold:
                            total_score += similarity * kw_weight * 0.5
                            matches += 1
                            break

        # Calculate final relevance score
        if matches > 0:
            # Simple and effective scoring:
            # - Base score of 0.3 for having any match
            # - Bonus for number of matches (up to 0.4 for 5+ matches)
            # - Bonus for match quality (up to 0.3)

            base_score = 0.3

            # Match count bonus: more matches = better relevance
            match_bonus = min(matches / 5, 1.0) * 0.4

            # Quality bonus: based on total weighted score
            quality_bonus = min(total_score / matches, 1.0) * 0.3 if matches > 0 else 0

            final_score = base_score + match_bonus + quality_bonus
        else:
            final_score = 0.0

        return min(final_score, 1.0)

    def clear_cache(self):
        """Clear the search cache."""
        self._cache.clear()


class SearchIndexManager:
    """
    Manages database indexes for optimal search performance.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def create_search_indexes(self):
        """Create indexes for all searchable collections."""

        index_configs = {
            'posts_table': [
                ('post_text', 'text'),
                ('key_narratives', 1),
                ('posted_at', -1)
            ],
            'print_daily': [
                ('content', 'text'),
                ('intelligence', 1),
                ('published_at', -1)
            ],
            'print_magazines': [
                ('content', 'text'),
                ('intelligence', 1),
                ('published_at', -1)
            ],
            'news_articles': [
                ('content', 'text'),
                ('keywords', 1),
                ('title', 'text'),
                ('published_date', -1)
            ],
            'link_crawl_logs': [
                ('source_pdf_id', 1),
                ('crawled_url', 1),
                ('created_at', -1)
            ]
        }

        for collection_name, indexes in index_configs.items():
            collection = self.db[collection_name]

            for index_spec in indexes:
                try:
                    if isinstance(index_spec, tuple):
                        field, direction = index_spec
                        if direction == 'text':
                            await collection.create_index(
                                [(field, 'text')],
                                background=True
                            )
                        else:
                            await collection.create_index(
                                [(field, direction)],
                                background=True
                            )
                except Exception as e:
                    logger.warning(f"Index creation warning for {collection_name}.{index_spec}: {e}")

        logger.info("Search indexes created/verified")
