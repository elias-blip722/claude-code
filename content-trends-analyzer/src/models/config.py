from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class Priority(str, Enum):
    """Priority levels"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class OutputFormat(str, Enum):
    """Output formats"""
    JSON = "json"
    CSV = "csv"
    HTML = "html"


class TwitterConfig(BaseModel):
    """Twitter/X specific configuration"""
    enabled: bool = True
    priority: Priority = Priority.HIGH
    rate_limit: str = "450/15min"
    accounts: List[str] = Field(default_factory=list)
    hashtags: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    exclude_keywords: List[str] = Field(default_factory=list)
    content_types: List[str] = Field(default_factory=lambda: ["text", "video", "image"])
    min_likes: int = 0
    min_retweets: int = 0
    verified_only: bool = False
    max_results: int = 100


class YouTubeConfig(BaseModel):
    """YouTube specific configuration"""
    enabled: bool = True
    priority: Priority = Priority.MEDIUM
    channels: List[str] = Field(default_factory=list)  # Channel IDs
    search_terms: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    min_views: int = 0
    min_likes: int = 0
    max_duration: Optional[int] = None  # seconds
    published_after: Optional[str] = None  # ISO format date
    max_results: int = 50


class MetaConfig(BaseModel):
    """Meta Content Library specific configuration"""
    enabled: bool = False  # Disabled by default until access obtained
    priority: Priority = Priority.MEDIUM
    keywords: List[str] = Field(default_factory=list)
    accounts: List[str] = Field(default_factory=list)
    content_types: List[str] = Field(default_factory=list)
    min_interactions: int = 0
    max_results: int = 50


class RSSConfig(BaseModel):
    """RSS feed configuration"""
    enabled: bool = True
    priority: Priority = Priority.LOW
    feeds: List[str] = Field(default_factory=list)  # Feed URLs
    keywords: List[str] = Field(default_factory=list)


class SourceConfig(BaseModel):
    """All source configurations"""
    twitter: TwitterConfig = Field(default_factory=TwitterConfig)
    youtube: YouTubeConfig = Field(default_factory=YouTubeConfig)
    meta: MetaConfig = Field(default_factory=MetaConfig)
    rss_feeds: RSSConfig = Field(default_factory=RSSConfig)


class TrendDetectionConfig(BaseModel):
    """Trend detection configuration"""
    enabled: bool = True
    min_mentions: int = 10
    time_window: str = "24h"
    growth_threshold: float = 2.0


class SentimentAnalysisConfig(BaseModel):
    """Sentiment analysis configuration"""
    enabled: bool = True


class ContentClusteringConfig(BaseModel):
    """Content clustering configuration"""
    enabled: bool = True
    algorithm: str = "kmeans"
    num_clusters: int = 5


class AnalysisConfig(BaseModel):
    """Analysis configuration"""
    trend_detection: TrendDetectionConfig = Field(default_factory=TrendDetectionConfig)
    sentiment_analysis: SentimentAnalysisConfig = Field(default_factory=SentimentAnalysisConfig)
    content_clustering: ContentClusteringConfig = Field(default_factory=ContentClusteringConfig)


class OutputDestination(BaseModel):
    """Output destination configuration"""
    type: str  # "file" or "webhook"
    path: Optional[str] = None
    url: Optional[str] = None


class OutputConfig(BaseModel):
    """Output configuration"""
    formats: List[OutputFormat] = Field(default_factory=lambda: [OutputFormat.JSON])
    destinations: List[OutputDestination] = Field(default_factory=list)
    schedule: str = "0 */6 * * *"  # Cron format


class SchedulingConfig(BaseModel):
    """Collection scheduling configuration"""
    twitter: str = "*/5 * * * *"  # Every 5 minutes
    youtube: str = "0 */2 * * *"  # Every 2 hours
    meta: str = "*/30 * * * *"  # Every 30 minutes
    rss_feeds: str = "0 */4 * * *"  # Every 4 hours


class MonitoringConfig(BaseModel):
    """Complete monitoring configuration"""
    name: str
    description: Optional[str] = None
    sources: SourceConfig = Field(default_factory=SourceConfig)
    analysis: AnalysisConfig = Field(default_factory=AnalysisConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    scheduling: SchedulingConfig = Field(default_factory=SchedulingConfig)

    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'MonitoringConfig':
        """Load configuration from YAML file"""
        import yaml
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data.get('monitoring_config', data))

    def to_yaml(self, yaml_path: str):
        """Save configuration to YAML file"""
        import yaml
        with open(yaml_path, 'w') as f:
            yaml.dump(
                {'monitoring_config': self.model_dump(mode='json')},
                f,
                default_flow_style=False,
                sort_keys=False
            )
