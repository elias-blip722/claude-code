from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class TrendType(str, Enum):
    """Type of trend"""
    HASHTAG = "hashtag"
    KEYWORD = "keyword"
    TOPIC = "topic"
    ACCOUNT = "account"


class PlatformMetrics(BaseModel):
    """Metrics per platform"""
    twitter: int = 0
    youtube: int = 0
    meta: int = 0
    reddit: int = 0
    rss: int = 0


class SentimentBreakdown(BaseModel):
    """Sentiment distribution"""
    positive: float = 0.0
    neutral: float = 0.0
    negative: float = 0.0

    def normalize(self):
        """Normalize to sum to 1.0"""
        total = self.positive + self.neutral + self.negative
        if total > 0:
            self.positive /= total
            self.neutral /= total
            self.negative /= total


class TrendMetrics(BaseModel):
    """Trend metrics"""
    mention_count: int = 0
    growth_rate: float = 0.0  # Multiplier (e.g., 3.5x)
    peak_time: Optional[datetime] = None
    platforms: PlatformMetrics = Field(default_factory=PlatformMetrics)
    unique_authors: int = 0
    total_engagement: int = 0
    average_sentiment: float = 0.0  # -1 to 1
    velocity_score: float = 0.0  # Rate of acceleration


class TrendItem(BaseModel):
    """Trend analysis result"""
    id: str
    name: str
    type: TrendType
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    time_window: str = "24h"  # e.g., "1h", "24h", "7d"
    metrics: TrendMetrics
    related_content: List[str] = Field(default_factory=list)  # Content IDs
    related_trends: List[str] = Field(default_factory=list)  # Trend IDs
    sentiment_breakdown: SentimentBreakdown = Field(default_factory=SentimentBreakdown)
    keywords: List[str] = Field(default_factory=list)
    top_authors: List[str] = Field(default_factory=list)  # Author IDs

    # Status
    active: bool = True
    archived: bool = False

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.model_dump(mode='json')

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrendItem':
        """Create from dictionary"""
        return cls.model_validate(data)

    def calculate_trend_score(self) -> float:
        """Calculate overall trend score"""
        # Weighted score based on multiple factors
        mention_score = min(self.metrics.mention_count / 1000, 1.0) * 0.3
        growth_score = min(self.metrics.growth_rate / 10, 1.0) * 0.3
        engagement_score = min(self.metrics.total_engagement / 10000, 1.0) * 0.2
        velocity_score = min(self.metrics.velocity_score / 5, 1.0) * 0.2

        return mention_score + growth_score + engagement_score + velocity_score
