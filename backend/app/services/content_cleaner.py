import re
import unicodedata
from app.config import get_settings

settings = get_settings()


class ContentCleaner:
    """Service for cleaning and normalizing extracted text."""

    def __init__(self):
        self.max_length = settings.MAX_CONTENT_LENGTH

    def clean(self, text: str) -> str:
        """
        Clean and normalize text content.
        Removes HTML, special chars, normalizes whitespace.
        """
        if not text:
            return ""

        # Remove HTML tags (if any remaining)
        text = self._remove_html_tags(text)

        # Normalize unicode characters
        text = self._normalize_unicode(text)

        # Remove URLs
        text = self._remove_urls(text)

        # Remove email addresses
        text = self._remove_emails(text)

        # Remove special characters but keep punctuation
        text = self._clean_special_chars(text)

        # Normalize whitespace
        text = self._normalize_whitespace(text)

        # Remove very short lines (likely noise)
        text = self._remove_short_lines(text)

        # Truncate if too long
        if len(text) > self.max_length:
            text = text[:self.max_length] + "..."

        return text.strip()

    def _remove_html_tags(self, text: str) -> str:
        """Remove any remaining HTML tags."""
        # Remove HTML comments
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", text)
        # Remove HTML entities
        text = re.sub(r"&[a-zA-Z]+;", " ", text)
        text = re.sub(r"&#\d+;", " ", text)
        return text

    def _normalize_unicode(self, text: str) -> str:
        """Normalize unicode characters to ASCII equivalents where possible."""
        # Normalize to NFKD form
        text = unicodedata.normalize("NFKD", text)
        # Remove non-ASCII characters that don't have ASCII equivalents
        # but keep common punctuation and letters
        text = text.encode("ascii", "ignore").decode("ascii")
        return text

    def _remove_urls(self, text: str) -> str:
        """Remove URLs from text."""
        url_pattern = r"https?://\S+|www\.\S+"
        return re.sub(url_pattern, "", text)

    def _remove_emails(self, text: str) -> str:
        """Remove email addresses from text."""
        email_pattern = r"\S+@\S+\.\S+"
        return re.sub(email_pattern, "", text)

    def _clean_special_chars(self, text: str) -> str:
        """Remove special characters but keep useful punctuation."""
        # Keep letters, numbers, and basic punctuation
        text = re.sub(r"[^\w\s.,!?;:'\"-]", " ", text)
        return text

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize all whitespace to single spaces."""
        # Replace multiple whitespace with single space
        text = re.sub(r"\s+", " ", text)
        # Replace multiple newlines with double newline
        text = re.sub(r"\n\s*\n", "\n\n", text)
        return text

    def _remove_short_lines(self, text: str, min_length: int = 20) -> str:
        """Remove very short lines that are likely navigation/noise."""
        lines = text.split("\n")
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            # Keep lines that are either long enough or look like sentences
            if len(line) >= min_length or (line and line[-1] in ".!?"):
                cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def get_word_count(self, text: str) -> int:
        """Get word count of text."""
        words = text.split()
        return len(words)

    def get_summary(self, text: str, max_sentences: int = 3) -> str:
        """Extract first few sentences as summary."""
        sentences = re.split(r"[.!?]+", text)
        summary_sentences = []

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 30:  # Skip very short sentences
                summary_sentences.append(sentence)
                if len(summary_sentences) >= max_sentences:
                    break

        return ". ".join(summary_sentences) + "." if summary_sentences else text[:200]
