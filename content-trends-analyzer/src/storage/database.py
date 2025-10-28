import os
import json
from datetime import datetime
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    Index,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Optional

Base = declarative_base()


class ContentItemDB(Base):
    """Database model for content items"""
    __tablename__ = "content_items"

    id = Column(String, primary_key=True)
    platform = Column(String, nullable=False, index=True)
    content_type = Column(String, nullable=False)
    url = Column(String, nullable=False)
    fingerprint = Column(String, unique=True, index=True)

    # Author (stored as JSON)
    author_id = Column(String, index=True)
    author_data = Column(Text)  # JSON

    # Content (stored as JSON)
    content_data = Column(Text)  # JSON

    # Metadata
    created_at = Column(DateTime, nullable=False, index=True)
    collected_at = Column(DateTime, nullable=False, index=True)
    language = Column(String)
    location = Column(String)

    # Engagement metrics
    likes = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    views = Column(Integer, default=0)
    engagement_rate = Column(Float, default=0.0)

    # Analysis
    sentiment = Column(String)
    sentiment_score = Column(Float)
    topics = Column(Text)  # JSON array
    relevance_score = Column(Float, default=0.0, index=True)
    trend_velocity = Column(Float, default=0.0)

    # Status
    processed = Column(Boolean, default=False)

    __table_args__ = (
        Index('idx_platform_created', 'platform', 'created_at'),
        Index('idx_relevance', 'relevance_score'),
    )


class TrendItemDB(Base):
    """Database model for trends"""
    __tablename__ = "trends"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False)
    detected_at = Column(DateTime, nullable=False, index=True)
    time_window = Column(String)

    # Metrics
    mention_count = Column(Integer, default=0)
    growth_rate = Column(Float, default=0.0, index=True)
    peak_time = Column(DateTime)
    unique_authors = Column(Integer, default=0)
    total_engagement = Column(Integer, default=0)
    velocity_score = Column(Float, default=0.0, index=True)

    # Related data (stored as JSON)
    platform_metrics = Column(Text)  # JSON
    related_content = Column(Text)  # JSON array
    related_trends = Column(Text)  # JSON array
    sentiment_breakdown = Column(Text)  # JSON
    keywords = Column(Text)  # JSON array
    top_authors = Column(Text)  # JSON array

    # Status
    active = Column(Boolean, default=True, index=True)
    archived = Column(Boolean, default=False)

    __table_args__ = (
        Index('idx_active_detected', 'active', 'detected_at'),
    )


class CollectionMetadata(Base):
    """Track collection runs and metadata"""
    __tablename__ = "collection_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String, nullable=False, index=True)
    collection_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    items_collected = Column(Integer, default=0)
    items_new = Column(Integer, default=0)
    items_duplicate = Column(Integer, default=0)
    errors = Column(Integer, default=0)
    metadata = Column(Text)  # JSON with additional info


class Database:
    """Database manager"""

    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_tables(self):
        """Create all tables"""
        Base.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        """Get a new database session"""
        return self.SessionLocal()

    def close(self):
        """Close database connection"""
        self.engine.dispose()


def init_database(database_url: Optional[str] = None) -> Database:
    """Initialize database"""
    if database_url is None:
        database_url = os.getenv("DATABASE_URL", "sqlite:///./data/content_trends.db")

    # Ensure directory exists for SQLite
    if database_url.startswith("sqlite:///"):
        db_path = database_url.replace("sqlite:///", "")
        os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)

    db = Database(database_url)
    db.create_tables()
    return db
