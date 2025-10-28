from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from ..models.content import ContentItem, Platform
from ..storage.repository import ContentRepository


class CollectionResult:
    """Result of a collection run"""

    def __init__(self):
        self.items_collected: int = 0
        self.items_new: int = 0
        self.items_duplicate: int = 0
        self.errors: int = 0
        self.error_messages: List[str] = []
        self.start_time: datetime = datetime.utcnow()
        self.end_time: Optional[datetime] = None

    def add_error(self, error: str):
        """Add an error message"""
        self.errors += 1
        self.error_messages.append(error)

    def finish(self):
        """Mark collection as finished"""
        self.end_time = datetime.utcnow()

    def get_duration(self) -> float:
        """Get collection duration in seconds"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "items_collected": self.items_collected,
            "items_new": self.items_new,
            "items_duplicate": self.items_duplicate,
            "errors": self.errors,
            "error_messages": self.error_messages,
            "duration_seconds": self.get_duration(),
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
        }


class BaseCollector(ABC):
    """Base class for all content collectors"""

    def __init__(
        self,
        platform: Platform,
        config: Dict[str, Any],
        repository: Optional[ContentRepository] = None
    ):
        self.platform = platform
        self.config = config
        self.repository = repository
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def collect(self) -> List[ContentItem]:
        """
        Collect content from the platform.

        Returns:
            List of collected content items
        """
        pass

    def save_items(self, items: List[ContentItem], result: CollectionResult) -> List[ContentItem]:
        """
        Save collected items to database.

        Args:
            items: List of content items
            result: Collection result to track statistics

        Returns:
            List of new (non-duplicate) items
        """
        if not self.repository:
            self.logger.warning("No repository configured, items will not be saved")
            return items

        new_items = []
        for item in items:
            try:
                # Check for duplicates using fingerprint
                if item.fingerprint and self.repository.exists_by_fingerprint(item.fingerprint):
                    result.items_duplicate += 1
                    self.logger.debug(f"Skipping duplicate item: {item.id}")
                    continue

                # Save to database
                self.repository.save(item)
                result.items_new += 1
                new_items.append(item)

            except Exception as e:
                result.add_error(f"Error saving item {item.id}: {str(e)}")
                self.logger.error(f"Error saving item {item.id}: {e}", exc_info=True)

        return new_items

    def run_collection(self) -> CollectionResult:
        """
        Run the complete collection process.

        Returns:
            Collection result with statistics
        """
        result = CollectionResult()

        try:
            self.logger.info(f"Starting collection for {self.platform.value}")

            # Collect items
            items = self.collect()
            result.items_collected = len(items)

            self.logger.info(f"Collected {len(items)} items from {self.platform.value}")

            # Save items
            if self.repository:
                new_items = self.save_items(items, result)
                self.logger.info(
                    f"Saved {result.items_new} new items, "
                    f"skipped {result.items_duplicate} duplicates"
                )

        except Exception as e:
            result.add_error(f"Collection error: {str(e)}")
            self.logger.error(f"Collection error: {e}", exc_info=True)

        finally:
            result.finish()

        return result

    def _generate_fingerprint(self, *args) -> str:
        """
        Generate a fingerprint for deduplication.

        Args:
            args: Values to include in fingerprint

        Returns:
            MD5 hash as fingerprint
        """
        import hashlib
        content = "|".join(str(arg) for arg in args)
        return hashlib.md5(content.encode()).hexdigest()

    def _parse_duration(self, duration_str: str) -> int:
        """
        Parse ISO 8601 duration string to seconds.

        Args:
            duration_str: Duration string like "PT4M13S"

        Returns:
            Duration in seconds
        """
        import re

        if not duration_str:
            return 0

        # Match pattern like PT4M13S
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
        if not match:
            return 0

        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)

        return hours * 3600 + minutes * 60 + seconds
