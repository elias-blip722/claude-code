import os
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

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
from ..models.config import TwitterConfig
from ..storage.repository import ContentRepository


class TwitterCollector(BaseCollector):
    """
    Twitter/X content collector using Twitter API v2.

    NOTE: This is a framework implementation ready for Twitter API integration.
    To activate:
    1. Obtain Twitter API credentials (API Key, API Secret, Bearer Token)
    2. Add credentials to .env file
    3. Install tweepy: pip install tweepy
    4. Uncomment the tweepy import and API initialization code below
    """

    def __init__(
        self,
        config: TwitterConfig,
        repository: Optional[ContentRepository] = None,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        bearer_token: Optional[str] = None,
        access_token: Optional[str] = None,
        access_token_secret: Optional[str] = None,
    ):
        super().__init__(Platform.TWITTER, config.model_dump(), repository)
        self.twitter_config = config

        # Get credentials from parameters or environment
        self.api_key = api_key or os.getenv("TWITTER_API_KEY")
        self.api_secret = api_secret or os.getenv("TWITTER_API_SECRET")
        self.bearer_token = bearer_token or os.getenv("TWITTER_BEARER_TOKEN")
        self.access_token = access_token or os.getenv("TWITTER_ACCESS_TOKEN")
        self.access_token_secret = access_token_secret or os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

        self.client = None

        # Check if credentials are available
        if self.bearer_token:
            self._initialize_client()
        else:
            self.logger.warning(
                "Twitter API credentials not found. "
                "This collector will not function until credentials are provided."
            )

    def _initialize_client(self):
        """Initialize Twitter API client"""
        try:
            # Uncomment when ready to use Twitter API:
            # import tweepy
            # self.client = tweepy.Client(
            #     bearer_token=self.bearer_token,
            #     consumer_key=self.api_key,
            #     consumer_secret=self.api_secret,
            #     access_token=self.access_token,
            #     access_token_secret=self.access_token_secret,
            #     wait_on_rate_limit=True
            # )
            self.logger.info("Twitter API client initialized (stub)")
        except Exception as e:
            self.logger.error(f"Error initializing Twitter client: {e}")

    def collect(self) -> List[ContentItem]:
        """Collect content from Twitter"""
        if not self.client and not self.bearer_token:
            self.logger.warning("Twitter API not configured. Returning empty results.")
            return []

        items = []

        try:
            # Search by keywords and hashtags
            if self.twitter_config.keywords or self.twitter_config.hashtags:
                search_items = self._search_tweets()
                items.extend(search_items)

            # Get tweets from specific accounts
            if self.twitter_config.accounts:
                for account in self.twitter_config.accounts:
                    account_items = self._get_user_tweets(account)
                    items.extend(account_items)

        except Exception as e:
            self.logger.error(f"Twitter collection error: {e}")

        return items

    def _search_tweets(self) -> List[ContentItem]:
        """
        Search for tweets by keywords and hashtags.

        IMPLEMENTATION GUIDE:
        1. Build search query from keywords and hashtags
        2. Use Twitter API v2 search_recent_tweets endpoint
        3. Apply filters (min_likes, min_retweets, verified_only)
        4. Parse results into ContentItem objects
        """
        items = []

        if not self.client:
            self.logger.debug("Twitter client not initialized - stub mode")
            return items

        # Build search query
        query = self._build_search_query()

        if not query:
            return items

        try:
            # Example implementation (uncomment when ready):
            # response = self.client.search_recent_tweets(
            #     query=query,
            #     max_results=self.twitter_config.max_results,
            #     tweet_fields=['created_at', 'public_metrics', 'entities', 'lang', 'possibly_sensitive'],
            #     user_fields=['username', 'name', 'verified', 'public_metrics', 'profile_image_url'],
            #     expansions=['author_id', 'attachments.media_keys'],
            #     media_fields=['url', 'preview_image_url', 'type', 'width', 'height']
            # )
            #
            # if response.data:
            #     for tweet in response.data:
            #         item = self._parse_tweet(tweet, response.includes)
            #         if item and self._meets_criteria(item):
            #             items.append(item)

            self.logger.info(f"Would search Twitter for: {query}")

        except Exception as e:
            self.logger.error(f"Error searching tweets: {e}")

        return items

    def _get_user_tweets(self, username: str) -> List[ContentItem]:
        """
        Get recent tweets from a specific user.

        IMPLEMENTATION GUIDE:
        1. Get user ID from username
        2. Use get_users_tweets endpoint
        3. Parse and filter results
        """
        items = []

        if not self.client:
            return items

        try:
            # Example implementation:
            # # Get user ID
            # user = self.client.get_user(username=username.lstrip('@'))
            # if not user.data:
            #     return items
            #
            # # Get tweets
            # response = self.client.get_users_tweets(
            #     id=user.data.id,
            #     max_results=self.twitter_config.max_results,
            #     tweet_fields=['created_at', 'public_metrics', 'entities', 'lang'],
            #     user_fields=['username', 'name', 'verified', 'public_metrics'],
            # )
            #
            # if response.data:
            #     for tweet in response.data:
            #         item = self._parse_tweet(tweet, response.includes)
            #         if item and self._meets_criteria(item):
            #             items.append(item)

            self.logger.info(f"Would get tweets from: {username}")

        except Exception as e:
            self.logger.error(f"Error getting tweets from {username}: {e}")

        return items

    def _parse_tweet(self, tweet: Dict[str, Any], includes: Optional[Dict] = None) -> Optional[ContentItem]:
        """
        Parse Twitter API response into ContentItem.

        IMPLEMENTATION GUIDE:
        - Extract tweet text, media, hashtags, mentions
        - Parse engagement metrics (likes, retweets, replies)
        - Create Author from user data
        - Handle media attachments
        """
        # Stub implementation - would parse actual tweet data
        self.logger.debug(f"Would parse tweet: {tweet}")
        return None

    def _build_search_query(self) -> str:
        """Build Twitter search query from configuration"""
        query_parts = []

        # Add keywords
        if self.twitter_config.keywords:
            keyword_query = ' OR '.join(f'"{kw}"' for kw in self.twitter_config.keywords)
            query_parts.append(f"({keyword_query})")

        # Add hashtags
        if self.twitter_config.hashtags:
            hashtag_query = ' OR '.join(self.twitter_config.hashtags)
            query_parts.append(f"({hashtag_query})")

        # Combine with AND
        query = ' '.join(query_parts)

        # Add exclusions
        if self.twitter_config.exclude_keywords:
            exclusions = ' '.join(f'-{kw}' for kw in self.twitter_config.exclude_keywords)
            query = f"{query} {exclusions}"

        # Add filters
        filters = []
        if self.twitter_config.verified_only:
            filters.append("is:verified")

        # Exclude retweets
        filters.append("-is:retweet")

        if filters:
            query = f"{query} {' '.join(filters)}"

        return query.strip()

    def _meets_criteria(self, item: ContentItem) -> bool:
        """Check if tweet meets configured criteria"""
        # Check minimum likes
        if item.engagement.likes < self.twitter_config.min_likes:
            return False

        # Check minimum retweets
        if item.engagement.shares < self.twitter_config.min_retweets:
            return False

        return True

    def get_rate_limit_status(self) -> Optional[Dict[str, Any]]:
        """
        Get current rate limit status.

        IMPLEMENTATION GUIDE:
        Use Twitter API to check remaining API calls
        """
        if not self.client:
            return None

        # Example:
        # return self.client.get_rate_limit_status()

        return {
            "status": "stub",
            "message": "Twitter API not initialized"
        }
