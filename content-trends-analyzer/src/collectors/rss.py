from typing import List, Optional, Dict, Any
from datetime import datetime
import feedparser
import time

from .base import BaseCollector
from ..models.content import (
    ContentItem,
    Platform,
    ContentType,
    Author,
    ContentData,
    Metadata,
    Engagement,
)
from ..models.config import RSSConfig
from ..storage.repository import ContentRepository


class RSSCollector(BaseCollector):
    """RSS feed collector"""

    def __init__(
        self,
        config: RSSConfig,
        repository: Optional[ContentRepository] = None
    ):
        super().__init__(Platform.RSS, config.model_dump(), repository)
        self.rss_config = config

    def collect(self) -> List[ContentItem]:
        """Collect content from RSS feeds"""
        items = []

        for feed_url in self.rss_config.feeds:
            try:
                feed_items = self._parse_feed(feed_url)
                items.extend(feed_items)
            except Exception as e:
                self.logger.error(f"Error parsing feed {feed_url}: {e}")

        return items

    def _parse_feed(self, feed_url: str) -> List[ContentItem]:
        """Parse a single RSS feed"""
        items = []

        try:
            self.logger.info(f"Parsing RSS feed: {feed_url}")

            # Parse the feed
            feed = feedparser.parse(feed_url)

            if feed.bozo:
                self.logger.warning(f"Feed {feed_url} has parsing issues: {feed.bozo_exception}")

            # Get feed info for author
            feed_title = feed.feed.get('title', 'Unknown Feed')
            feed_link = feed.feed.get('link', feed_url)

            # Process entries
            for entry in feed.entries:
                try:
                    item = self._parse_entry(entry, feed_title, feed_link, feed_url)
                    if item and self._meets_criteria(item):
                        items.append(item)
                except Exception as e:
                    self.logger.error(f"Error parsing entry: {e}")

            self.logger.info(f"Parsed {len(items)} items from {feed_url}")

        except Exception as e:
            self.logger.error(f"Error parsing feed {feed_url}: {e}")

        return items

    def _parse_entry(
        self,
        entry: Dict[str, Any],
        feed_title: str,
        feed_link: str,
        feed_url: str
    ) -> Optional[ContentItem]:
        """Parse a single feed entry into ContentItem"""

        # Get entry link
        link = entry.get('link', '')
        if not link:
            return None

        # Get published date
        published_at = self._parse_date(entry)

        # Get author info
        author_name = (
            entry.get('author', '') or
            feed_title
        )

        # Create author
        author = Author(
            id=self._generate_fingerprint(feed_url),
            username=feed_title,
            display_name=author_name,
            verified=False,
        )

        # Get content
        title = entry.get('title', 'Untitled')
        summary = self._get_entry_content(entry)

        # Extract hashtags from content
        hashtags = self._extract_hashtags(f"{title} {summary}")

        # Create content data
        content = ContentData(
            title=title,
            description=summary,
            text=f"{title}\n\n{summary}",
            hashtags=hashtags,
            urls=[link],
        )

        # Create metadata
        metadata = Metadata(
            created_at=published_at,
            collected_at=datetime.utcnow(),
            language=self._detect_language(summary),
        )

        # RSS feeds typically don't have engagement metrics
        engagement = Engagement()

        # Generate unique ID
        entry_id = entry.get('id', link)
        content_id = f"rss_{self._generate_fingerprint(entry_id)}"

        # Create content item
        content_item = ContentItem(
            id=content_id,
            platform=Platform.RSS,
            content_type=ContentType.TEXT,
            url=link,
            author=author,
            content=content,
            metadata=metadata,
            engagement=engagement,
            fingerprint=self._generate_fingerprint(Platform.RSS.value, entry_id),
        )

        return content_item

    def _parse_date(self, entry: Dict[str, Any]) -> datetime:
        """Parse publication date from entry"""
        # Try different date fields
        date_fields = ['published_parsed', 'updated_parsed', 'created_parsed']

        for field in date_fields:
            if field in entry and entry[field]:
                try:
                    time_tuple = entry[field]
                    return datetime.fromtimestamp(time.mktime(time_tuple))
                except Exception:
                    pass

        # Try string dates
        string_fields = ['published', 'updated', 'created']
        for field in string_fields:
            if field in entry and entry[field]:
                try:
                    return datetime.fromisoformat(entry[field].replace('Z', '+00:00'))
                except Exception:
                    pass

        # Default to now
        return datetime.utcnow()

    def _get_entry_content(self, entry: Dict[str, Any]) -> str:
        """Extract content from entry"""
        # Try different content fields in order of preference
        if 'content' in entry and entry['content']:
            # content is usually a list of dictionaries
            return entry['content'][0].get('value', '')

        if 'summary' in entry:
            return entry['summary']

        if 'description' in entry:
            return entry['description']

        return ''

    def _meets_criteria(self, item: ContentItem) -> bool:
        """Check if item meets configured criteria"""
        # Check keywords
        if self.rss_config.keywords:
            content_text = (
                f"{item.content.title} {item.content.description}"
            ).lower()

            # Check if any keyword matches
            has_keyword = any(
                keyword.lower() in content_text
                for keyword in self.rss_config.keywords
            )

            if not has_keyword:
                return False

        return True

    def _extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from text"""
        import re
        if not text:
            return []

        hashtags = re.findall(r'#(\w+)', text)
        return list(set(hashtags))

    def _detect_language(self, text: str) -> Optional[str]:
        """
        Detect language of text.

        Simple implementation - could be enhanced with language detection library.
        """
        if not text:
            return None

        # Simple heuristic - could use langdetect or other library
        # For now, just return None
        return None

    def validate_feed(self, feed_url: str) -> Dict[str, Any]:
        """Validate an RSS feed"""
        try:
            feed = feedparser.parse(feed_url)

            return {
                "valid": not feed.bozo,
                "title": feed.feed.get('title', 'Unknown'),
                "link": feed.feed.get('link', ''),
                "entries": len(feed.entries),
                "error": str(feed.bozo_exception) if feed.bozo else None
            }

        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }
