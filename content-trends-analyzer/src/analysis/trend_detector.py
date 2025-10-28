from typing import List, Dict, Set, Tuple
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import logging
import hashlib

from ..models.content import ContentItem, Platform
from ..models.trend import (
    TrendItem,
    TrendType,
    TrendMetrics,
    PlatformMetrics,
    SentimentBreakdown,
)
from ..models.config import TrendDetectionConfig


class TrendDetector:
    """Detect trends from content items"""

    def __init__(self, config: TrendDetectionConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def detect_trends(
        self,
        items: List[ContentItem],
        historical_items: Optional[List[ContentItem]] = None
    ) -> List[TrendItem]:
        """
        Detect trends from content items.

        Args:
            items: Current content items
            historical_items: Previous items for comparison

        Returns:
            List of detected trends
        """
        trends = []

        # Detect hashtag trends
        hashtag_trends = self._detect_hashtag_trends(items, historical_items)
        trends.extend(hashtag_trends)

        # Detect keyword trends
        keyword_trends = self._detect_keyword_trends(items, historical_items)
        trends.extend(keyword_trends)

        # Detect topic trends
        topic_trends = self._detect_topic_trends(items, historical_items)
        trends.extend(topic_trends)

        # Sort by trend score
        trends.sort(key=lambda t: t.calculate_trend_score(), reverse=True)

        return trends

    def _detect_hashtag_trends(
        self,
        items: List[ContentItem],
        historical_items: Optional[List[ContentItem]] = None
    ) -> List[TrendItem]:
        """Detect trending hashtags"""
        trends = []

        # Count hashtags in current items
        current_hashtags = self._count_hashtags(items)

        # Count hashtags in historical items
        historical_hashtags = {}
        if historical_items:
            historical_hashtags = self._count_hashtags(historical_items)

        # Find trending hashtags
        for hashtag, count in current_hashtags.items():
            # Check minimum mentions
            if count < self.config.min_mentions:
                continue

            # Calculate growth rate
            historical_count = historical_hashtags.get(hashtag, 0)
            growth_rate = self._calculate_growth_rate(count, historical_count)

            # Check growth threshold
            if growth_rate >= self.config.growth_threshold:
                trend = self._create_hashtag_trend(
                    hashtag,
                    items,
                    count,
                    growth_rate
                )
                trends.append(trend)

        return trends

    def _detect_keyword_trends(
        self,
        items: List[ContentItem],
        historical_items: Optional[List[ContentItem]] = None
    ) -> List[TrendItem]:
        """Detect trending keywords"""
        trends = []

        # Extract keywords from items
        current_keywords = self._count_keywords(items)
        historical_keywords = {}

        if historical_items:
            historical_keywords = self._count_keywords(historical_items)

        # Find trending keywords
        for keyword, count in current_keywords.items():
            if count < self.config.min_mentions:
                continue

            historical_count = historical_keywords.get(keyword, 0)
            growth_rate = self._calculate_growth_rate(count, historical_count)

            if growth_rate >= self.config.growth_threshold:
                trend = self._create_keyword_trend(
                    keyword,
                    items,
                    count,
                    growth_rate
                )
                trends.append(trend)

        return trends

    def _detect_topic_trends(
        self,
        items: List[ContentItem],
        historical_items: Optional[List[ContentItem]] = None
    ) -> List[TrendItem]:
        """Detect trending topics"""
        trends = []

        # Count topics in current items
        current_topics = self._count_topics(items)
        historical_topics = {}

        if historical_items:
            historical_topics = self._count_topics(historical_items)

        # Find trending topics
        for topic, count in current_topics.items():
            if count < self.config.min_mentions:
                continue

            historical_count = historical_topics.get(topic, 0)
            growth_rate = self._calculate_growth_rate(count, historical_count)

            if growth_rate >= self.config.growth_threshold:
                trend = self._create_topic_trend(
                    topic,
                    items,
                    count,
                    growth_rate
                )
                trends.append(trend)

        return trends

    def _count_hashtags(self, items: List[ContentItem]) -> Dict[str, int]:
        """Count hashtag occurrences"""
        hashtags = []
        for item in items:
            hashtags.extend(item.content.hashtags)

        return Counter(hashtags)

    def _count_keywords(self, items: List[ContentItem]) -> Dict[str, int]:
        """Count keyword occurrences"""
        keywords = []
        for item in items:
            if item.analysis and item.analysis.keywords:
                keywords.extend(item.analysis.keywords)

        return Counter(keywords)

    def _count_topics(self, items: List[ContentItem]) -> Dict[str, int]:
        """Count topic occurrences"""
        topics = []
        for item in items:
            if item.analysis and item.analysis.topics:
                topics.extend(item.analysis.topics)

        return Counter(topics)

    def _calculate_growth_rate(self, current: int, historical: int) -> float:
        """Calculate growth rate multiplier"""
        if historical == 0:
            return float(current) if current > 0 else 0.0

        return current / historical

    def _create_hashtag_trend(
        self,
        hashtag: str,
        items: List[ContentItem],
        mention_count: int,
        growth_rate: float
    ) -> TrendItem:
        """Create a hashtag trend item"""
        # Filter items with this hashtag
        related_items = [
            item for item in items
            if hashtag in item.content.hashtags
        ]

        return self._create_trend(
            name=f"#{hashtag}",
            trend_type=TrendType.HASHTAG,
            items=related_items,
            mention_count=mention_count,
            growth_rate=growth_rate
        )

    def _create_keyword_trend(
        self,
        keyword: str,
        items: List[ContentItem],
        mention_count: int,
        growth_rate: float
    ) -> TrendItem:
        """Create a keyword trend item"""
        # Filter items with this keyword
        related_items = [
            item for item in items
            if item.analysis and keyword in item.analysis.keywords
        ]

        return self._create_trend(
            name=keyword,
            trend_type=TrendType.KEYWORD,
            items=related_items,
            mention_count=mention_count,
            growth_rate=growth_rate
        )

    def _create_topic_trend(
        self,
        topic: str,
        items: List[ContentItem],
        mention_count: int,
        growth_rate: float
    ) -> TrendItem:
        """Create a topic trend item"""
        # Filter items with this topic
        related_items = [
            item for item in items
            if item.analysis and topic in item.analysis.topics
        ]

        return self._create_trend(
            name=topic,
            trend_type=TrendType.TOPIC,
            items=related_items,
            mention_count=mention_count,
            growth_rate=growth_rate
        )

    def _create_trend(
        self,
        name: str,
        trend_type: TrendType,
        items: List[ContentItem],
        mention_count: int,
        growth_rate: float
    ) -> TrendItem:
        """Create a trend item from related content"""
        # Calculate metrics
        platform_counts = self._count_by_platform(items)
        unique_authors = len(set(item.author.id for item in items))
        total_engagement = sum(
            item.engagement.likes +
            item.engagement.shares +
            item.engagement.comments
            for item in items
        )

        # Find peak time
        peak_time = self._find_peak_time(items)

        # Calculate velocity score (mentions per hour)
        velocity_score = self._calculate_velocity(items)

        # Create platform metrics
        platform_metrics = PlatformMetrics(
            twitter=platform_counts.get(Platform.TWITTER, 0),
            youtube=platform_counts.get(Platform.YOUTUBE, 0),
            meta=platform_counts.get(Platform.META, 0),
            rss=platform_counts.get(Platform.RSS, 0),
        )

        # Create metrics
        metrics = TrendMetrics(
            mention_count=mention_count,
            growth_rate=growth_rate,
            peak_time=peak_time,
            platforms=platform_metrics,
            unique_authors=unique_authors,
            total_engagement=total_engagement,
            velocity_score=velocity_score,
        )

        # Calculate sentiment breakdown
        sentiment_breakdown = self._calculate_sentiment_breakdown(items)

        # Get top authors
        top_authors = self._get_top_authors(items, limit=10)

        # Extract keywords
        keywords = self._extract_trend_keywords(items)

        # Generate ID
        trend_id = self._generate_trend_id(name, trend_type)

        # Create trend
        trend = TrendItem(
            id=trend_id,
            name=name,
            type=trend_type,
            detected_at=datetime.utcnow(),
            time_window=self.config.time_window,
            metrics=metrics,
            related_content=[item.id for item in items[:100]],  # Limit to 100
            sentiment_breakdown=sentiment_breakdown,
            keywords=keywords,
            top_authors=top_authors,
        )

        return trend

    def _count_by_platform(self, items: List[ContentItem]) -> Dict[Platform, int]:
        """Count items by platform"""
        counts = defaultdict(int)
        for item in items:
            counts[item.platform] += 1
        return dict(counts)

    def _find_peak_time(self, items: List[ContentItem]) -> datetime:
        """Find peak time for trend"""
        if not items:
            return datetime.utcnow()

        # Group by hour and count
        hour_counts = defaultdict(int)
        for item in items:
            hour = item.metadata.created_at.replace(minute=0, second=0, microsecond=0)
            hour_counts[hour] += 1

        # Find hour with most items
        if hour_counts:
            peak_hour = max(hour_counts.items(), key=lambda x: x[1])[0]
            return peak_hour

        return datetime.utcnow()

    def _calculate_velocity(self, items: List[ContentItem]) -> float:
        """Calculate trend velocity (mentions per hour)"""
        if not items:
            return 0.0

        # Find time range
        timestamps = [item.metadata.created_at for item in items]
        min_time = min(timestamps)
        max_time = max(timestamps)

        time_diff = (max_time - min_time).total_seconds() / 3600  # hours

        if time_diff == 0:
            return float(len(items))

        return len(items) / time_diff

    def _calculate_sentiment_breakdown(self, items: List[ContentItem]) -> SentimentBreakdown:
        """Calculate sentiment distribution"""
        breakdown = SentimentBreakdown()

        sentiment_counts = Counter()
        for item in items:
            if item.analysis and item.analysis.sentiment:
                sentiment_counts[item.analysis.sentiment] += 1

        total = sum(sentiment_counts.values())
        if total > 0:
            from ..models.content import Sentiment
            breakdown.positive = sentiment_counts.get(Sentiment.POSITIVE, 0) / total
            breakdown.neutral = sentiment_counts.get(Sentiment.NEUTRAL, 0) / total
            breakdown.negative = sentiment_counts.get(Sentiment.NEGATIVE, 0) / total

        return breakdown

    def _get_top_authors(self, items: List[ContentItem], limit: int = 10) -> List[str]:
        """Get top authors by engagement"""
        author_engagement = defaultdict(int)

        for item in items:
            engagement = (
                item.engagement.likes +
                item.engagement.shares +
                item.engagement.comments
            )
            author_engagement[item.author.id] += engagement

        # Sort by engagement
        sorted_authors = sorted(
            author_engagement.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [author_id for author_id, _ in sorted_authors[:limit]]

    def _extract_trend_keywords(self, items: List[ContentItem], limit: int = 20) -> List[str]:
        """Extract keywords related to trend"""
        all_keywords = []
        for item in items:
            if item.analysis and item.analysis.keywords:
                all_keywords.extend(item.analysis.keywords)

        # Count and get top keywords
        keyword_counts = Counter(all_keywords)
        return [kw for kw, _ in keyword_counts.most_common(limit)]

    def _generate_trend_id(self, name: str, trend_type: TrendType) -> str:
        """Generate unique trend ID"""
        content = f"{trend_type.value}_{name}_{datetime.utcnow().strftime('%Y%m%d')}"
        return hashlib.md5(content.encode()).hexdigest()
