from typing import Tuple
import logging

from ..models.content import ContentItem, Sentiment


class SentimentAnalyzer:
    """
    Analyze sentiment of content.

    Uses TextBlob for simple sentiment analysis.
    Can be enhanced with more sophisticated models.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._initialize_analyzer()

    def _initialize_analyzer(self):
        """Initialize sentiment analysis tools"""
        try:
            from textblob import TextBlob
            self.textblob_available = True
        except ImportError:
            self.logger.warning(
                "TextBlob not available. Sentiment analysis will use fallback method."
            )
            self.textblob_available = False

    def analyze(self, item: ContentItem) -> Tuple[Sentiment, float]:
        """
        Analyze sentiment of content item.

        Returns:
            Tuple of (sentiment classification, sentiment score)
            Score ranges from -1 (very negative) to 1 (very positive)
        """
        # Get text content
        text = self._get_text(item)

        if not text:
            return Sentiment.NEUTRAL, 0.0

        if self.textblob_available:
            return self._analyze_with_textblob(text)
        else:
            return self._analyze_with_fallback(text)

    def _get_text(self, item: ContentItem) -> str:
        """Extract text from content item"""
        text_parts = []

        if item.content.title:
            text_parts.append(item.content.title)

        if item.content.description:
            text_parts.append(item.content.description)

        if item.content.text:
            text_parts.append(item.content.text)

        return ' '.join(text_parts)

    def _analyze_with_textblob(self, text: str) -> Tuple[Sentiment, float]:
        """Analyze sentiment using TextBlob"""
        try:
            from textblob import TextBlob

            blob = TextBlob(text)
            polarity = blob.sentiment.polarity  # -1 to 1

            # Classify sentiment
            if polarity > 0.1:
                sentiment = Sentiment.POSITIVE
            elif polarity < -0.1:
                sentiment = Sentiment.NEGATIVE
            else:
                sentiment = Sentiment.NEUTRAL

            return sentiment, polarity

        except Exception as e:
            self.logger.error(f"Error analyzing sentiment: {e}")
            return Sentiment.NEUTRAL, 0.0

    def _analyze_with_fallback(self, text: str) -> Tuple[Sentiment, float]:
        """Simple keyword-based sentiment analysis"""
        text_lower = text.lower()

        # Positive keywords
        positive_keywords = {
            'good', 'great', 'excellent', 'amazing', 'awesome', 'wonderful',
            'fantastic', 'love', 'best', 'perfect', 'happy', 'beautiful',
            'brilliant', 'outstanding', 'incredible', 'superb', 'delightful'
        }

        # Negative keywords
        negative_keywords = {
            'bad', 'terrible', 'awful', 'horrible', 'worst', 'hate',
            'disappointing', 'poor', 'useless', 'waste', 'annoying',
            'frustrating', 'pathetic', 'disgusting', 'failure'
        }

        # Count occurrences
        positive_count = sum(1 for word in positive_keywords if word in text_lower)
        negative_count = sum(1 for word in negative_keywords if word in text_lower)

        # Calculate score
        total = positive_count + negative_count
        if total == 0:
            return Sentiment.NEUTRAL, 0.0

        score = (positive_count - negative_count) / total

        # Classify
        if score > 0.2:
            sentiment = Sentiment.POSITIVE
        elif score < -0.2:
            sentiment = Sentiment.NEGATIVE
        else:
            sentiment = Sentiment.NEUTRAL

        return sentiment, score

    def batch_analyze(self, items: List[ContentItem]) -> List[ContentItem]:
        """Analyze sentiment for a batch of items"""
        for item in items:
            try:
                sentiment, score = self.analyze(item)

                if not item.analysis:
                    from ..models.content import Analysis
                    item.analysis = Analysis()

                item.analysis.sentiment = sentiment
                item.analysis.sentiment_score = score

            except Exception as e:
                self.logger.error(f"Error analyzing item {item.id}: {e}")

        return items
