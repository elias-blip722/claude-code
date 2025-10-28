import hashlib
import re
from typing import List, Set, Optional
from collections import Counter
import logging

from ..models.content import ContentItem, Analysis, Sentiment


class ContentProcessor:
    """Process and enrich content items"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._seen_fingerprints: Set[str] = set()

    def process_batch(self, items: List[ContentItem]) -> List[ContentItem]:
        """
        Process a batch of content items.

        Applies:
        - Deduplication
        - Normalization
        - Basic analysis
        - Keyword extraction
        """
        processed = []

        for item in items:
            try:
                # Skip duplicates
                if self.is_duplicate(item):
                    continue

                # Normalize
                self.normalize(item)

                # Add basic analysis if not present
                if not item.analysis:
                    item.analysis = self.analyze_content(item)

                # Calculate relevance score
                item.analysis.relevance_score = self.calculate_relevance(item)

                processed.append(item)

            except Exception as e:
                self.logger.error(f"Error processing item {item.id}: {e}")

        return processed

    def is_duplicate(self, item: ContentItem) -> bool:
        """Check if item is a duplicate"""
        if not item.fingerprint:
            return False

        if item.fingerprint in self._seen_fingerprints:
            return True

        self._seen_fingerprints.add(item.fingerprint)
        return False

    def normalize(self, item: ContentItem):
        """Normalize content item"""
        # Normalize text
        if item.content.text:
            item.content.text = self._normalize_text(item.content.text)

        # Normalize title
        if item.content.title:
            item.content.title = self._normalize_text(item.content.title)

        # Normalize description
        if item.content.description:
            item.content.description = self._normalize_text(item.content.description)

        # Normalize hashtags (lowercase, remove #)
        if item.content.hashtags:
            item.content.hashtags = [
                tag.lower().lstrip('#') for tag in item.content.hashtags
            ]

        # Deduplicate hashtags
        if item.content.hashtags:
            item.content.hashtags = list(set(item.content.hashtags))

    def _normalize_text(self, text: str) -> str:
        """Normalize text content"""
        if not text:
            return ""

        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Strip leading/trailing whitespace
        text = text.strip()

        return text

    def analyze_content(self, item: ContentItem) -> Analysis:
        """Perform basic content analysis"""
        analysis = Analysis()

        # Extract keywords
        analysis.keywords = self.extract_keywords(item)

        # Extract topics (basic - from hashtags)
        analysis.topics = item.content.hashtags[:10] if item.content.hashtags else []

        # Basic sentiment (will be enhanced by SentimentAnalyzer)
        analysis.sentiment = Sentiment.NEUTRAL
        analysis.sentiment_score = 0.0

        # Calculate spam score
        analysis.spam_score = self.calculate_spam_score(item)

        return analysis

    def extract_keywords(self, item: ContentItem, max_keywords: int = 10) -> List[str]:
        """Extract keywords from content"""
        # Combine all text
        text_parts = []

        if item.content.title:
            text_parts.append(item.content.title)

        if item.content.description:
            text_parts.append(item.content.description)

        if item.content.text:
            text_parts.append(item.content.text)

        text = ' '.join(text_parts).lower()

        # Remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this',
            'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
            'what', 'which', 'who', 'when', 'where', 'why', 'how'
        }

        # Extract words (alphanumeric + hyphen)
        words = re.findall(r'\b[a-z0-9][\w-]*\b', text)

        # Filter and count
        word_counts = Counter(
            word for word in words
            if len(word) > 3 and word not in stop_words
        )

        # Get top keywords
        keywords = [word for word, count in word_counts.most_common(max_keywords)]

        return keywords

    def calculate_relevance(self, item: ContentItem, keywords: Optional[List[str]] = None) -> float:
        """
        Calculate relevance score for content.

        Factors:
        - Engagement metrics
        - Keyword matches (if provided)
        - Content quality indicators
        - Recency
        """
        score = 0.0

        # Engagement score (normalized to 0-1)
        engagement_score = min(
            (item.engagement.likes * 1.0 +
             item.engagement.shares * 2.0 +
             item.engagement.comments * 1.5) / 1000,
            1.0
        )
        score += engagement_score * 0.4

        # Views score (normalized)
        if item.engagement.views > 0:
            views_score = min(item.engagement.views / 100000, 1.0)
            score += views_score * 0.2

        # Keyword match score
        if keywords and item.analysis and item.analysis.keywords:
            keyword_matches = len(set(keywords) & set(item.analysis.keywords))
            keyword_score = min(keyword_matches / len(keywords), 1.0)
            score += keyword_score * 0.3

        # Content quality (has title, description, not spam)
        quality_score = 0.0
        if item.content.title:
            quality_score += 0.3
        if item.content.description:
            quality_score += 0.3
        if item.analysis and item.analysis.spam_score < 0.3:
            quality_score += 0.4

        score += quality_score * 0.1

        return min(score, 1.0)

    def calculate_spam_score(self, item: ContentItem) -> float:
        """
        Calculate spam probability score.

        Returns score from 0 (not spam) to 1 (definitely spam).
        """
        score = 0.0

        text = (item.content.text or '').lower()

        # Check for excessive hashtags
        if item.content.hashtags and len(item.content.hashtags) > 10:
            score += 0.2

        # Check for excessive links
        if item.content.urls and len(item.content.urls) > 5:
            score += 0.2

        # Check for spam keywords
        spam_keywords = [
            'buy now', 'click here', 'limited time', 'act now',
            'congratulations', 'you won', 'claim your', 'free money',
            'make money fast', 'work from home', 'get rich'
        ]

        spam_count = sum(1 for keyword in spam_keywords if keyword in text)
        if spam_count > 0:
            score += min(spam_count * 0.15, 0.4)

        # Check for excessive capitalization
        if text:
            caps_ratio = sum(1 for c in text if c.isupper()) / len(text)
            if caps_ratio > 0.5:
                score += 0.2

        return min(score, 1.0)

    def deduplicate_items(self, items: List[ContentItem]) -> List[ContentItem]:
        """Remove duplicate items from list"""
        seen = set()
        unique_items = []

        for item in items:
            if item.fingerprint and item.fingerprint not in seen:
                seen.add(item.fingerprint)
                unique_items.append(item)

        return unique_items

    def merge_similar_items(self, items: List[ContentItem], similarity_threshold: float = 0.8) -> List[ContentItem]:
        """
        Merge similar items (reposts, shares).

        This is a placeholder for more advanced similarity detection.
        """
        # For now, just return items as-is
        # In production, you might use:
        # - Text similarity (cosine similarity of TF-IDF vectors)
        # - Image perceptual hashing
        # - URL matching after normalization

        return items
