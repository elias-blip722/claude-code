from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl


class Platform(str, Enum):
    """Supported platforms"""
    TWITTER = "twitter"
    YOUTUBE = "youtube"
    META = "meta"
    REDDIT = "reddit"
    RSS = "rss"
    BLOG = "blog"


class ContentType(str, Enum):
    """Content types"""
    TEXT = "text"
    VIDEO = "video"
    IMAGE = "image"
    AUDIO = "audio"
    MIXED = "mixed"


class Sentiment(str, Enum):
    """Sentiment classification"""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"


class MediaItem(BaseModel):
    """Media item within content"""
    type: str
    url: str
    thumbnail: Optional[str] = None
    duration: Optional[int] = None  # seconds for video/audio
    width: Optional[int] = None
    height: Optional[int] = None


class Author(BaseModel):
    """Content author/creator"""
    id: str
    username: Optional[str] = None
    display_name: Optional[str] = None
    verified: bool = False
    follower_count: Optional[int] = None
    profile_url: Optional[str] = None
    avatar_url: Optional[str] = None


class ContentData(BaseModel):
    """Main content data"""
    text: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    media: List[MediaItem] = Field(default_factory=list)
    hashtags: List[str] = Field(default_factory=list)
    mentions: List[str] = Field(default_factory=list)
    urls: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)


class Metadata(BaseModel):
    """Content metadata"""
    created_at: datetime
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    language: Optional[str] = None
    location: Optional[str] = None
    platform_specific: Dict[str, Any] = Field(default_factory=dict)


class Engagement(BaseModel):
    """Engagement metrics"""
    likes: int = 0
    shares: int = 0
    comments: int = 0
    views: int = 0
    saves: int = 0
    engagement_rate: float = 0.0

    def calculate_engagement_rate(self) -> float:
        """Calculate engagement rate"""
        if self.views == 0:
            return 0.0
        total_engagement = self.likes + self.shares + self.comments + self.saves
        return (total_engagement / self.views) * 100


class Analysis(BaseModel):
    """Content analysis results"""
    sentiment: Optional[Sentiment] = None
    sentiment_score: Optional[float] = None  # -1 to 1
    topics: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    relevance_score: float = 0.0
    trend_velocity: float = 0.0  # Rate of growth
    spam_score: float = 0.0


class ContentItem(BaseModel):
    """Complete content item model"""
    id: str
    platform: Platform
    content_type: ContentType
    url: str
    author: Author
    content: ContentData
    metadata: Metadata
    engagement: Engagement
    analysis: Optional[Analysis] = None

    # Internal tracking
    fingerprint: Optional[str] = None  # For deduplication
    processed: bool = False

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.model_dump(mode='json')

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContentItem':
        """Create from dictionary"""
        return cls.model_validate(data)
