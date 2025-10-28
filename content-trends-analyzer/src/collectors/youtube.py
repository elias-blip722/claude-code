import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .base import BaseCollector
from ..models.content import (
    ContentItem,
    Platform,
    ContentType,
    Author,
    ContentData,
    Metadata,
    Engagement,
    MediaItem,
)
from ..models.config import YouTubeConfig
from ..storage.repository import ContentRepository


class YouTubeCollector(BaseCollector):
    """YouTube content collector using Google API"""

    def __init__(
        self,
        config: YouTubeConfig,
        repository: Optional[ContentRepository] = None,
        api_key: Optional[str] = None
    ):
        super().__init__(Platform.YOUTUBE, config.model_dump(), repository)
        self.youtube_config = config
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY") or os.getenv("GOOGLE_API_KEY")

        if not self.api_key:
            raise ValueError("YouTube API key not provided")

        self.youtube = build('youtube', 'v3', developerKey=self.api_key)

    def collect(self) -> List[ContentItem]:
        """Collect content from YouTube"""
        items = []

        try:
            # Collect from search terms
            if self.youtube_config.search_terms:
                for term in self.youtube_config.search_terms:
                    search_items = self._search_videos(term)
                    items.extend(search_items)

            # Collect from specific channels
            if self.youtube_config.channels:
                for channel_id in self.youtube_config.channels:
                    channel_items = self._get_channel_videos(channel_id)
                    items.extend(channel_items)

        except HttpError as e:
            self.logger.error(f"YouTube API error: {e}")
            raise

        return items

    def _search_videos(self, query: str) -> List[ContentItem]:
        """Search for videos by query"""
        items = []

        try:
            # Build search parameters
            search_params = {
                'q': query,
                'part': 'snippet',
                'type': 'video',
                'maxResults': self.youtube_config.max_results,
                'order': 'date',
            }

            # Add published after filter
            if self.youtube_config.published_after:
                search_params['publishedAfter'] = self.youtube_config.published_after

            # Execute search
            response = self.youtube.search().list(**search_params).execute()

            # Get video IDs
            video_ids = [item['id']['videoId'] for item in response.get('items', [])]

            if video_ids:
                # Get detailed video information
                items = self._get_video_details(video_ids)

        except HttpError as e:
            self.logger.error(f"Error searching YouTube for '{query}': {e}")

        return items

    def _get_channel_videos(self, channel_id: str) -> List[ContentItem]:
        """Get recent videos from a channel"""
        items = []

        try:
            # Search for videos from this channel
            search_params = {
                'channelId': channel_id,
                'part': 'snippet',
                'type': 'video',
                'maxResults': self.youtube_config.max_results,
                'order': 'date',
            }

            if self.youtube_config.published_after:
                search_params['publishedAfter'] = self.youtube_config.published_after

            response = self.youtube.search().list(**search_params).execute()

            video_ids = [item['id']['videoId'] for item in response.get('items', [])]

            if video_ids:
                items = self._get_video_details(video_ids)

        except HttpError as e:
            self.logger.error(f"Error getting videos from channel {channel_id}: {e}")

        return items

    def _get_video_details(self, video_ids: List[str]) -> List[ContentItem]:
        """Get detailed information for videos"""
        items = []

        try:
            # Fetch video details (can request up to 50 at a time)
            for i in range(0, len(video_ids), 50):
                batch_ids = video_ids[i:i + 50]

                response = self.youtube.videos().list(
                    part='snippet,statistics,contentDetails',
                    id=','.join(batch_ids)
                ).execute()

                for video in response.get('items', []):
                    try:
                        item = self._parse_video(video)
                        if item and self._meets_criteria(item):
                            items.append(item)
                    except Exception as e:
                        self.logger.error(f"Error parsing video {video.get('id')}: {e}")

        except HttpError as e:
            self.logger.error(f"Error getting video details: {e}")

        return items

    def _parse_video(self, video: Dict[str, Any]) -> Optional[ContentItem]:
        """Parse YouTube video data into ContentItem"""
        video_id = video['id']
        snippet = video['snippet']
        statistics = video.get('statistics', {})
        content_details = video.get('contentDetails', {})

        # Parse published date
        published_at = datetime.fromisoformat(
            snippet['publishedAt'].replace('Z', '+00:00')
        )

        # Create author
        author = Author(
            id=snippet['channelId'],
            username=snippet['channelTitle'],
            display_name=snippet['channelTitle'],
            verified=False,  # Would need additional API call to check
        )

        # Parse thumbnails
        thumbnails = snippet.get('thumbnails', {})
        thumbnail_url = (
            thumbnails.get('maxres', {}).get('url') or
            thumbnails.get('high', {}).get('url') or
            thumbnails.get('default', {}).get('url')
        )

        # Parse duration
        duration_str = content_details.get('duration', 'PT0S')
        duration_seconds = self._parse_duration(duration_str)

        # Create media item
        media = MediaItem(
            type='video',
            url=f"https://www.youtube.com/watch?v={video_id}",
            thumbnail=thumbnail_url,
            duration=duration_seconds,
        )

        # Create content data
        content = ContentData(
            title=snippet['title'],
            description=snippet.get('description', ''),
            text=f"{snippet['title']}\n\n{snippet.get('description', '')}",
            media=[media],
            hashtags=self._extract_hashtags(snippet.get('description', '')),
            categories=[snippet.get('categoryId', '')],
        )

        # Parse engagement metrics
        engagement = Engagement(
            likes=int(statistics.get('likeCount', 0)),
            comments=int(statistics.get('commentCount', 0)),
            views=int(statistics.get('viewCount', 0)),
            shares=0,  # YouTube API doesn't provide share count
        )
        engagement.engagement_rate = engagement.calculate_engagement_rate()

        # Create metadata
        metadata = Metadata(
            created_at=published_at,
            collected_at=datetime.utcnow(),
            language=snippet.get('defaultLanguage') or snippet.get('defaultAudioLanguage'),
        )

        # Create content item
        content_item = ContentItem(
            id=f"youtube_{video_id}",
            platform=Platform.YOUTUBE,
            content_type=ContentType.VIDEO,
            url=f"https://www.youtube.com/watch?v={video_id}",
            author=author,
            content=content,
            metadata=metadata,
            engagement=engagement,
            fingerprint=self._generate_fingerprint(Platform.YOUTUBE.value, video_id),
        )

        return content_item

    def _meets_criteria(self, item: ContentItem) -> bool:
        """Check if video meets configured criteria"""
        # Check minimum views
        if item.engagement.views < self.youtube_config.min_views:
            return False

        # Check minimum likes
        if item.engagement.likes < self.youtube_config.min_likes:
            return False

        # Check maximum duration
        if self.youtube_config.max_duration:
            video_duration = 0
            if item.content.media:
                video_duration = item.content.media[0].duration or 0

            if video_duration > self.youtube_config.max_duration:
                return False

        return True

    def _extract_hashtags(self, text: str) -> List[str]:
        """Extract hashtags from text"""
        import re
        if not text:
            return []

        # Find all hashtags
        hashtags = re.findall(r'#(\w+)', text)
        return list(set(hashtags))  # Remove duplicates

    def get_channel_info(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get channel information"""
        try:
            response = self.youtube.channels().list(
                part='snippet,statistics',
                id=channel_id
            ).execute()

            if response.get('items'):
                return response['items'][0]

        except HttpError as e:
            self.logger.error(f"Error getting channel info: {e}")

        return None
