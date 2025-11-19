import spacy
from collections import Counter
from typing import Optional
from app.config import get_settings
from app.models.schemas import KeywordItem, EntityExtraction

settings = get_settings()


class KeywordExtractor:
    """
    Service for extracting keywords and named entities using spaCy NLP.

    How it works:
    1. Process text with spaCy pipeline
    2. Extract named entities (people, places, organizations)
    3. Extract important noun phrases
    4. Extract significant individual nouns/proper nouns
    5. Score and rank keywords by frequency and importance
    6. Return top N keywords with scores and types
    """

    def __init__(self):
        self.nlp: Optional[spacy.language.Language] = None
        self._load_model()

        # Words to ignore (stop words + common non-informative words)
        self.stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
            "be", "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "must", "shall", "can", "need",
            "dare", "ought", "used", "said", "says", "say", "also", "just",
            "even", "because", "so", "if", "when", "than", "that", "this",
            "these", "those", "then", "there", "here", "where", "which", "who",
            "whom", "whose", "what", "how", "why", "all", "each", "every",
            "both", "few", "more", "most", "other", "some", "such", "no", "not",
            "only", "own", "same", "so", "than", "too", "very", "just", "about",
            "after", "before", "between", "into", "through", "during", "above",
            "below", "up", "down", "out", "off", "over", "under", "again",
            "further", "once", "here", "there", "when", "where", "why", "how",
            "any", "many", "much", "new", "first", "last", "long", "great",
            "little", "old", "right", "big", "high", "different", "small",
            "large", "next", "early", "young", "important", "public", "bad",
            "good", "make", "made", "way", "time", "year", "years", "day",
            "days", "thing", "things", "man", "men", "woman", "women", "child",
            "world", "life", "hand", "part", "place", "case", "week", "company",
            "system", "program", "question", "work", "government", "number",
            "night", "point", "home", "water", "room", "mother", "area", "money",
            "story", "fact", "month", "lot", "right", "study", "book", "eye",
            "job", "word", "business", "issue", "side", "kind", "head", "house",
            "service", "friend", "father", "power", "hour", "game", "line",
            "end", "member", "law", "car", "city", "community", "name"
        }

    def _load_model(self):
        """Load spaCy model."""
        try:
            self.nlp = spacy.load(settings.SPACY_MODEL)
            print(f"Loaded spaCy model: {settings.SPACY_MODEL}")
        except OSError:
            # Download model if not found
            print(f"Downloading spaCy model: {settings.SPACY_MODEL}")
            spacy.cli.download(settings.SPACY_MODEL)
            self.nlp = spacy.load(settings.SPACY_MODEL)

    def extract(self, text: str, max_keywords: int = 10) -> tuple[list[KeywordItem], EntityExtraction]:
        """
        Extract keywords and entities from text.

        Returns:
            tuple: (list of KeywordItems, EntityExtraction)
        """
        if not text or not self.nlp:
            return [], EntityExtraction()

        # Process text with spaCy
        doc = self.nlp(text)

        # Extract named entities
        entities = self._extract_entities(doc)

        # Extract keywords from various sources
        keyword_scores = Counter()

        # 1. Add named entities as keywords (high weight)
        for ent in doc.ents:
            if len(ent.text) > 2 and ent.label_ in [
                "PERSON", "ORG", "GPE", "LOC", "EVENT", "PRODUCT", "WORK_OF_ART"
            ]:
                keyword = ent.text.strip().lower()
                if self._is_valid_keyword(keyword):
                    keyword_scores[keyword] += 3  # Higher weight for entities

        # 2. Extract noun chunks (phrases)
        for chunk in doc.noun_chunks:
            # Get the root noun and its modifiers
            chunk_text = chunk.text.strip().lower()

            # Skip if too short or contains stop words only
            words = chunk_text.split()
            meaningful_words = [w for w in words if w not in self.stop_words]

            if len(meaningful_words) >= 1 and len(chunk_text) > 3:
                if self._is_valid_keyword(chunk_text):
                    keyword_scores[chunk_text] += 2

        # 3. Extract individual important nouns and proper nouns
        for token in doc:
            if token.pos_ in ["NOUN", "PROPN"] and not token.is_stop:
                word = token.lemma_.lower().strip()
                if self._is_valid_keyword(word) and len(word) > 2:
                    keyword_scores[word] += 1

        # 4. Get top keywords
        keywords = self._rank_keywords(keyword_scores, max_keywords, doc)

        return keywords, entities

    def _extract_entities(self, doc) -> EntityExtraction:
        """Extract named entities organized by type."""
        entities = EntityExtraction()

        for ent in doc.ents:
            text = ent.text.strip()

            if ent.label_ == "PERSON":
                if text not in entities.persons:
                    entities.persons.append(text)
            elif ent.label_ in ["GPE", "LOC"]:
                if text not in entities.locations:
                    entities.locations.append(text)
            elif ent.label_ == "ORG":
                if text not in entities.organizations:
                    entities.organizations.append(text)
            elif ent.label_ == "DATE":
                if text not in entities.dates:
                    entities.dates.append(text)
            else:
                if text not in entities.misc and len(text) > 2:
                    entities.misc.append(text)

        return entities

    def _is_valid_keyword(self, keyword: str) -> bool:
        """Check if keyword is valid (not a stop word, has content)."""
        if not keyword:
            return False

        # Remove punctuation for checking
        clean = keyword.strip().lower()

        # Check if it's just stop words
        words = clean.split()
        meaningful = [w for w in words if w not in self.stop_words]

        if not meaningful:
            return False

        # Check minimum length
        if len(clean) < 3:
            return False

        # Check if it's mostly numbers
        alpha_chars = sum(1 for c in clean if c.isalpha())
        if alpha_chars < len(clean) * 0.5:
            return False

        return True

    def _rank_keywords(self, keyword_scores: Counter, max_keywords: int, doc) -> list[KeywordItem]:
        """Rank and format keywords with scores and types."""
        if not keyword_scores:
            return []

        # Get max score for normalization
        max_score = max(keyword_scores.values()) if keyword_scores else 1

        # Create keyword items
        keywords = []
        entity_texts = {ent.text.lower() for ent in doc.ents}

        # No limit - get all keywords (or use max_keywords if specified and less than 100)
        limit = max_keywords if max_keywords and max_keywords < 100 else None

        for keyword, score in keyword_scores.most_common(limit):
            # Normalize score to 0-1
            normalized_score = round(score / max_score, 2)

            # Determine type
            if keyword in entity_texts:
                keyword_type = "entity"
            elif " " in keyword:
                keyword_type = "phrase"
            else:
                keyword_type = "noun"

            keywords.append(KeywordItem(
                keyword=keyword,
                score=normalized_score,
                type=keyword_type
            ))

        # Sort by score and return all keywords (no limit)
        keywords.sort(key=lambda x: x.score, reverse=True)
        return keywords

    def is_loaded(self) -> bool:
        """Check if NLP model is loaded."""
        return self.nlp is not None
