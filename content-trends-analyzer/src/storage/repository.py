import json
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_

from .database import ContentItemDB, TrendItemDB, CollectionMetadata
from ..models.content import ContentItem, Platform
from ..models.trend import TrendItem


class ContentRepository:
    """Repository for content items"""

    def __init__(self, session: Session):
        self.session = session

    def save(self, content: ContentItem) -> ContentItemDB:
        """Save content item to database"""
        db_item = ContentItemDB(
            id=content.id,
            platform=content.platform.value,
            content_type=content.content_type.value,
            url=content.url,
            fingerprint=content.fingerprint,
            author_id=content.author.id,
            author_data=json.dumps(content.author.model_dump(mode='json')),
            content_data=json.dumps(content.content.model_dump(mode='json')),
            created_at=content.metadata.created_at,
            collected_at=content.metadata.collected_at,
            language=content.metadata.language,
            location=content.metadata.location,
            likes=content.engagement.likes,
            shares=content.engagement.shares,
            comments=content.engagement.comments,
            views=content.engagement.views,
            engagement_rate=content.engagement.engagement_rate,
            processed=content.processed,
        )

        if content.analysis:
            db_item.sentiment = content.analysis.sentiment.value if content.analysis.sentiment else None
            db_item.sentiment_score = content.analysis.sentiment_score
            db_item.topics = json.dumps(content.analysis.topics)
            db_item.relevance_score = content.analysis.relevance_score
            db_item.trend_velocity = content.analysis.trend_velocity

        self.session.merge(db_item)
        self.session.commit()
        return db_item

    def get_by_id(self, content_id: str) -> Optional[ContentItem]:
        """Get content item by ID"""
        db_item = self.session.query(ContentItemDB).filter_by(id=content_id).first()
        if db_item:
            return self._to_model(db_item)
        return None

    def get_by_fingerprint(self, fingerprint: str) -> Optional[ContentItem]:
        """Get content item by fingerprint"""
        db_item = self.session.query(ContentItemDB).filter_by(fingerprint=fingerprint).first()
        if db_item:
            return self._to_model(db_item)
        return None

    def exists_by_fingerprint(self, fingerprint: str) -> bool:
        """Check if content exists by fingerprint"""
        return self.session.query(ContentItemDB).filter_by(fingerprint=fingerprint).count() > 0

    def get_recent(
        self,
        platform: Optional[Platform] = None,
        hours: int = 24,
        limit: int = 100
    ) -> List[ContentItem]:
        """Get recent content items"""
        query = self.session.query(ContentItemDB)

        since = datetime.utcnow() - timedelta(hours=hours)
        query = query.filter(ContentItemDB.collected_at >= since)

        if platform:
            query = query.filter(ContentItemDB.platform == platform.value)

        query = query.order_by(desc(ContentItemDB.collected_at)).limit(limit)

        return [self._to_model(item) for item in query.all()]

    def get_by_keywords(
        self,
        keywords: List[str],
        platform: Optional[Platform] = None,
        hours: Optional[int] = None,
        limit: int = 100
    ) -> List[ContentItem]:
        """Get content items matching keywords"""
        query = self.session.query(ContentItemDB)

        if hours:
            since = datetime.utcnow() - timedelta(hours=hours)
            query = query.filter(ContentItemDB.collected_at >= since)

        if platform:
            query = query.filter(ContentItemDB.platform == platform.value)

        # Search in content_data JSON
        keyword_filters = []
        for keyword in keywords:
            keyword_filters.append(ContentItemDB.content_data.like(f'%{keyword}%'))

        if keyword_filters:
            query = query.filter(or_(*keyword_filters))

        query = query.order_by(desc(ContentItemDB.relevance_score)).limit(limit)

        return [self._to_model(item) for item in query.all()]

    def count_by_platform(self, platform: Platform, hours: int = 24) -> int:
        """Count content items by platform"""
        since = datetime.utcnow() - timedelta(hours=hours)
        return self.session.query(ContentItemDB).filter(
            and_(
                ContentItemDB.platform == platform.value,
                ContentItemDB.collected_at >= since
            )
        ).count()

    def _to_model(self, db_item: ContentItemDB) -> ContentItem:
        """Convert database model to Pydantic model"""
        from ..models.content import Author, ContentData, Metadata, Engagement, Analysis, Sentiment

        author_data = json.loads(db_item.author_data)
        content_data = json.loads(db_item.content_data)

        content = ContentItem(
            id=db_item.id,
            platform=Platform(db_item.platform),
            content_type=db_item.content_type,
            url=db_item.url,
            author=Author(**author_data),
            content=ContentData(**content_data),
            metadata=Metadata(
                created_at=db_item.created_at,
                collected_at=db_item.collected_at,
                language=db_item.language,
                location=db_item.location,
            ),
            engagement=Engagement(
                likes=db_item.likes,
                shares=db_item.shares,
                comments=db_item.comments,
                views=db_item.views,
                engagement_rate=db_item.engagement_rate,
            ),
            fingerprint=db_item.fingerprint,
            processed=db_item.processed,
        )

        if db_item.sentiment:
            content.analysis = Analysis(
                sentiment=Sentiment(db_item.sentiment),
                sentiment_score=db_item.sentiment_score,
                topics=json.loads(db_item.topics) if db_item.topics else [],
                relevance_score=db_item.relevance_score,
                trend_velocity=db_item.trend_velocity,
            )

        return content


class TrendRepository:
    """Repository for trends"""

    def __init__(self, session: Session):
        self.session = session

    def save(self, trend: TrendItem) -> TrendItemDB:
        """Save trend to database"""
        db_trend = TrendItemDB(
            id=trend.id,
            name=trend.name,
            type=trend.type.value,
            detected_at=trend.detected_at,
            time_window=trend.time_window,
            mention_count=trend.metrics.mention_count,
            growth_rate=trend.metrics.growth_rate,
            peak_time=trend.metrics.peak_time,
            unique_authors=trend.metrics.unique_authors,
            total_engagement=trend.metrics.total_engagement,
            velocity_score=trend.metrics.velocity_score,
            platform_metrics=json.dumps(trend.metrics.platforms.model_dump(mode='json')),
            related_content=json.dumps(trend.related_content),
            related_trends=json.dumps(trend.related_trends),
            sentiment_breakdown=json.dumps(trend.sentiment_breakdown.model_dump(mode='json')),
            keywords=json.dumps(trend.keywords),
            top_authors=json.dumps(trend.top_authors),
            active=trend.active,
            archived=trend.archived,
        )

        self.session.merge(db_trend)
        self.session.commit()
        return db_trend

    def get_by_id(self, trend_id: str) -> Optional[TrendItem]:
        """Get trend by ID"""
        db_trend = self.session.query(TrendItemDB).filter_by(id=trend_id).first()
        if db_trend:
            return self._to_model(db_trend)
        return None

    def get_active(self, limit: int = 50) -> List[TrendItem]:
        """Get active trends"""
        db_trends = self.session.query(TrendItemDB).filter_by(
            active=True
        ).order_by(desc(TrendItemDB.velocity_score)).limit(limit).all()

        return [self._to_model(trend) for trend in db_trends]

    def get_recent(self, hours: int = 24, limit: int = 50) -> List[TrendItem]:
        """Get recent trends"""
        since = datetime.utcnow() - timedelta(hours=hours)
        db_trends = self.session.query(TrendItemDB).filter(
            TrendItemDB.detected_at >= since
        ).order_by(desc(TrendItemDB.detected_at)).limit(limit).all()

        return [self._to_model(trend) for trend in db_trends]

    def _to_model(self, db_trend: TrendItemDB) -> TrendItem:
        """Convert database model to Pydantic model"""
        from ..models.trend import TrendType, TrendMetrics, PlatformMetrics, SentimentBreakdown

        return TrendItem(
            id=db_trend.id,
            name=db_trend.name,
            type=TrendType(db_trend.type),
            detected_at=db_trend.detected_at,
            time_window=db_trend.time_window,
            metrics=TrendMetrics(
                mention_count=db_trend.mention_count,
                growth_rate=db_trend.growth_rate,
                peak_time=db_trend.peak_time,
                platforms=PlatformMetrics(**json.loads(db_trend.platform_metrics)),
                unique_authors=db_trend.unique_authors,
                total_engagement=db_trend.total_engagement,
                velocity_score=db_trend.velocity_score,
            ),
            related_content=json.loads(db_trend.related_content),
            related_trends=json.loads(db_trend.related_trends),
            sentiment_breakdown=SentimentBreakdown(**json.loads(db_trend.sentiment_breakdown)),
            keywords=json.loads(db_trend.keywords),
            top_authors=json.loads(db_trend.top_authors),
            active=db_trend.active,
            archived=db_trend.archived,
        )
