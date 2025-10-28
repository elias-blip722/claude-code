"""
Simple scheduler for automated content collection.

This provides a basic scheduling system for running collections
at specified intervals.
"""

import time
import logging
from datetime import datetime
from typing import Callable, Dict
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger


class Scheduler:
    """Schedule automated content collection"""

    def __init__(self):
        self.scheduler = BlockingScheduler()
        self.logger = logging.getLogger(__name__)
        self.jobs: Dict[str, str] = {}

    def add_job(
        self,
        job_id: str,
        func: Callable,
        cron_expr: str,
        **kwargs
    ):
        """
        Add a scheduled job.

        Args:
            job_id: Unique identifier for the job
            func: Function to execute
            cron_expr: Cron expression (e.g., "*/5 * * * *" for every 5 minutes)
            **kwargs: Additional arguments to pass to the function
        """
        try:
            trigger = CronTrigger.from_crontab(cron_expr)

            self.scheduler.add_job(
                func,
                trigger=trigger,
                id=job_id,
                name=job_id,
                kwargs=kwargs,
                replace_existing=True
            )

            self.jobs[job_id] = cron_expr
            self.logger.info(f"Scheduled job '{job_id}' with schedule: {cron_expr}")

        except Exception as e:
            self.logger.error(f"Error scheduling job '{job_id}': {e}")
            raise

    def remove_job(self, job_id: str):
        """Remove a scheduled job"""
        try:
            self.scheduler.remove_job(job_id)
            self.jobs.pop(job_id, None)
            self.logger.info(f"Removed job: {job_id}")
        except Exception as e:
            self.logger.error(f"Error removing job '{job_id}': {e}")

    def start(self):
        """Start the scheduler"""
        try:
            self.logger.info("Starting scheduler...")
            self.logger.info(f"Scheduled jobs: {len(self.jobs)}")

            for job_id, schedule in self.jobs.items():
                self.logger.info(f"  - {job_id}: {schedule}")

            self.scheduler.start()

        except (KeyboardInterrupt, SystemExit):
            self.logger.info("Scheduler stopped by user")
            self.stop()

        except Exception as e:
            self.logger.error(f"Scheduler error: {e}")
            raise

    def stop(self):
        """Stop the scheduler"""
        self.scheduler.shutdown()
        self.logger.info("Scheduler stopped")

    def list_jobs(self):
        """List all scheduled jobs"""
        return self.scheduler.get_jobs()


def create_collection_scheduler(config_path: str, db_url: str = None):
    """
    Create a scheduler for automated content collection.

    Args:
        config_path: Path to configuration file
        db_url: Optional database URL

    Returns:
        Configured Scheduler instance
    """
    from ..models.config import MonitoringConfig
    from ..storage import init_database, ContentRepository
    from ..collectors import YouTubeCollector, TwitterCollector, MetaCollector, RSSCollector

    # Load configuration
    config = MonitoringConfig.from_yaml(config_path)

    # Initialize database
    database = init_database(db_url)

    scheduler = Scheduler()

    def collect_youtube():
        """Collect from YouTube"""
        if not config.sources.youtube.enabled:
            return

        session = database.get_session()
        repository = ContentRepository(session)

        try:
            collector = YouTubeCollector(config.sources.youtube, repository)
            result = collector.run_collection()
            logging.info(
                f"YouTube collection: {result.items_collected} items, "
                f"{result.items_new} new"
            )
        finally:
            session.close()

    def collect_twitter():
        """Collect from Twitter"""
        if not config.sources.twitter.enabled:
            return

        session = database.get_session()
        repository = ContentRepository(session)

        try:
            collector = TwitterCollector(config.sources.twitter, repository)
            result = collector.run_collection()
            logging.info(
                f"Twitter collection: {result.items_collected} items, "
                f"{result.items_new} new"
            )
        finally:
            session.close()

    def collect_meta():
        """Collect from Meta"""
        if not config.sources.meta.enabled:
            return

        session = database.get_session()
        repository = ContentRepository(session)

        try:
            collector = MetaCollector(config.sources.meta, repository)
            result = collector.run_collection()
            logging.info(
                f"Meta collection: {result.items_collected} items, "
                f"{result.items_new} new"
            )
        finally:
            session.close()

    def collect_rss():
        """Collect from RSS"""
        if not config.sources.rss_feeds.enabled:
            return

        session = database.get_session()
        repository = ContentRepository(session)

        try:
            collector = RSSCollector(config.sources.rss_feeds, repository)
            result = collector.run_collection()
            logging.info(
                f"RSS collection: {result.items_collected} items, "
                f"{result.items_new} new"
            )
        finally:
            session.close()

    # Add jobs based on configuration
    if config.sources.youtube.enabled:
        scheduler.add_job(
            "youtube_collection",
            collect_youtube,
            config.scheduling.youtube
        )

    if config.sources.twitter.enabled:
        scheduler.add_job(
            "twitter_collection",
            collect_twitter,
            config.scheduling.twitter
        )

    if config.sources.meta.enabled:
        scheduler.add_job(
            "meta_collection",
            collect_meta,
            config.scheduling.meta
        )

    if config.sources.rss_feeds.enabled:
        scheduler.add_job(
            "rss_collection",
            collect_rss,
            config.scheduling.rss_feeds
        )

    return scheduler
