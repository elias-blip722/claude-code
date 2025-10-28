#!/usr/bin/env python3
"""
Content Trends Analyzer CLI

Command-line interface for the Content Trends Analyzer tool.
"""

import os
import sys
import click
import logging
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Content Trends Analyzer - Monitor and analyze social media trends"""
    pass


@cli.command()
@click.option('--config', '-c', type=click.Path(exists=True), required=True,
              help='Path to configuration YAML file')
@click.option('--output', '-o', type=click.Path(), default='./reports',
              help='Output directory for reports')
@click.option('--db', type=str, default=None,
              help='Database URL (default: from config or env)')
def collect(config: str, output: str, db: Optional[str]):
    """Collect content from configured sources"""
    try:
        from .models.config import MonitoringConfig
        from .storage import init_database, ContentRepository
        from .collectors import YouTubeCollector, TwitterCollector, MetaCollector, RSSCollector
        from .analysis import ContentProcessor

        # Load configuration
        click.echo(f"Loading configuration from {config}...")
        monitoring_config = MonitoringConfig.from_yaml(config)

        # Initialize database
        db_url = db or os.getenv("DATABASE_URL", "sqlite:///./data/content_trends.db")
        click.echo(f"Initializing database: {db_url}")
        database = init_database(db_url)
        session = database.get_session()
        repository = ContentRepository(session)

        # Initialize processor
        processor = ContentProcessor()

        # Collect from each enabled source
        all_items = []

        # YouTube
        if monitoring_config.sources.youtube.enabled:
            click.echo("\n📹 Collecting from YouTube...")
            try:
                collector = YouTubeCollector(
                    monitoring_config.sources.youtube,
                    repository
                )
                result = collector.run_collection()
                click.echo(f"  Collected: {result.items_collected} items")
                click.echo(f"  New: {result.items_new} | Duplicates: {result.items_duplicate}")
                if result.errors > 0:
                    click.echo(f"  ⚠️  Errors: {result.errors}", err=True)
            except Exception as e:
                click.echo(f"  ❌ Error: {e}", err=True)

        # Twitter
        if monitoring_config.sources.twitter.enabled:
            click.echo("\n🐦 Collecting from Twitter/X...")
            try:
                collector = TwitterCollector(
                    monitoring_config.sources.twitter,
                    repository
                )
                result = collector.run_collection()
                click.echo(f"  Collected: {result.items_collected} items")
                if result.errors > 0:
                    click.echo(f"  ⚠️  Errors: {result.errors}", err=True)
            except Exception as e:
                click.echo(f"  ⚠️  {e}", err=True)

        # Meta
        if monitoring_config.sources.meta.enabled:
            click.echo("\n📘 Collecting from Meta Content Library...")
            try:
                collector = MetaCollector(
                    monitoring_config.sources.meta,
                    repository
                )
                result = collector.run_collection()
                click.echo(f"  Collected: {result.items_collected} items")
                if result.errors > 0:
                    click.echo(f"  ⚠️  Errors: {result.errors}", err=True)
            except Exception as e:
                click.echo(f"  ⚠️  {e}", err=True)

        # RSS
        if monitoring_config.sources.rss_feeds.enabled:
            click.echo("\n📰 Collecting from RSS feeds...")
            try:
                collector = RSSCollector(
                    monitoring_config.sources.rss_feeds,
                    repository
                )
                result = collector.run_collection()
                click.echo(f"  Collected: {result.items_collected} items")
                click.echo(f"  New: {result.items_new} | Duplicates: {result.items_duplicate}")
                if result.errors > 0:
                    click.echo(f"  ⚠️  Errors: {result.errors}", err=True)
            except Exception as e:
                click.echo(f"  ❌ Error: {e}", err=True)

        click.echo("\n✅ Collection complete!")

        session.close()
        database.close()

    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        logger.exception("Collection error")
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', type=click.Path(exists=True), required=True,
              help='Path to configuration YAML file')
@click.option('--output', '-o', type=click.Path(), default='./reports',
              help='Output directory for reports')
@click.option('--db', type=str, default=None,
              help='Database URL')
@click.option('--hours', type=int, default=24,
              help='Analyze content from last N hours')
def analyze(config: str, output: str, db: Optional[str], hours: int):
    """Analyze collected content and detect trends"""
    try:
        from .models.config import MonitoringConfig
        from .storage import init_database, ContentRepository, TrendRepository
        from .analysis import TrendDetector, SentimentAnalyzer
        from .reporting import ReportGenerator

        # Load configuration
        click.echo(f"Loading configuration from {config}...")
        monitoring_config = MonitoringConfig.from_yaml(config)

        # Initialize database
        db_url = db or os.getenv("DATABASE_URL", "sqlite:///./data/content_trends.db")
        database = init_database(db_url)
        session = database.get_session()
        content_repo = ContentRepository(session)
        trend_repo = TrendRepository(session)

        # Get recent content
        click.echo(f"\n📊 Analyzing content from last {hours} hours...")
        items = content_repo.get_recent(hours=hours, limit=10000)
        click.echo(f"  Found {len(items)} content items")

        if not items:
            click.echo("  No content to analyze")
            return

        # Sentiment analysis
        if monitoring_config.analysis.sentiment_analysis.enabled:
            click.echo("\n😊 Running sentiment analysis...")
            sentiment_analyzer = SentimentAnalyzer()
            items = sentiment_analyzer.batch_analyze(items)

            # Update items in database
            for item in items:
                content_repo.save(item)

        # Trend detection
        if monitoring_config.analysis.trend_detection.enabled:
            click.echo("\n🔥 Detecting trends...")
            trend_detector = TrendDetector(monitoring_config.analysis.trend_detection)

            # Get historical data for comparison
            historical_items = content_repo.get_recent(hours=hours*2, limit=10000)

            trends = trend_detector.detect_trends(items, historical_items)
            click.echo(f"  Detected {len(trends)} trends")

            # Save trends
            for trend in trends:
                trend_repo.save(trend)

            # Generate report
            click.echo(f"\n📄 Generating reports in {output}...")
            report_gen = ReportGenerator(monitoring_config.output, output)
            output_files = report_gen.generate_report(items, trends)

            click.echo("\n✅ Reports generated:")
            for format_type, filepath in output_files.items():
                if isinstance(filepath, dict):
                    for name, path in filepath.items():
                        click.echo(f"  - {name}: {path}")
                else:
                    click.echo(f"  - {format_type}: {filepath}")

        session.close()
        database.close()

    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        logger.exception("Analysis error")
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', type=click.Path(exists=True), required=True,
              help='Path to configuration YAML file')
@click.option('--output', '-o', type=click.Path(), default='./reports',
              help='Output directory for reports')
@click.option('--db', type=str, default=None,
              help='Database URL')
def run(config: str, output: str, db: Optional[str]):
    """Run full pipeline: collect, analyze, and report"""
    click.echo("🚀 Running full pipeline...\n")

    # Collect
    ctx = click.get_current_context()
    ctx.invoke(collect, config=config, output=output, db=db)

    # Analyze
    click.echo("\n" + "="*50 + "\n")
    ctx.invoke(analyze, config=config, output=output, db=db, hours=24)

    click.echo("\n✅ Pipeline complete!")


@cli.command()
@click.option('--name', '-n', required=True, help='Configuration name')
@click.option('--output', '-o', type=click.Path(), required=True,
              help='Output path for configuration file')
def init_config(name: str, output: str):
    """Create a sample configuration file"""
    try:
        from .models.config import (
            MonitoringConfig, SourceConfig, TwitterConfig,
            YouTubeConfig, MetaConfig, RSSConfig,
            AnalysisConfig, OutputConfig, SchedulingConfig
        )

        # Create sample configuration
        config = MonitoringConfig(
            name=name,
            description="Sample monitoring configuration",
            sources=SourceConfig(),
            analysis=AnalysisConfig(),
            output=OutputConfig(),
            scheduling=SchedulingConfig()
        )

        # Save to file
        config.to_yaml(output)
        click.echo(f"✅ Configuration created: {output}")
        click.echo("\nEdit the file to customize your monitoring setup.")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--config', '-c', type=click.Path(exists=True), required=True,
              help='Path to configuration YAML file')
@click.option('--db', type=str, default=None,
              help='Database URL')
def schedule(config: str, db: Optional[str]):
    """Run scheduled automated collection"""
    try:
        from .utils.scheduler import create_collection_scheduler

        click.echo("⏰ Starting scheduled collection...\n")

        db_url = db or os.getenv("DATABASE_URL", "sqlite:///./data/content_trends.db")
        scheduler = create_collection_scheduler(config, db_url)

        click.echo("Scheduled jobs:")
        for job in scheduler.list_jobs():
            click.echo(f"  - {job.name}")

        click.echo("\nPress Ctrl+C to stop\n")

        scheduler.start()

    except KeyboardInterrupt:
        click.echo("\n\n⏹  Scheduler stopped by user")
    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        logger.exception("Scheduler error")
        sys.exit(1)


@cli.command()
@click.option('--db', type=str, default=None, help='Database URL')
def status(db: Optional[str]):
    """Show status and statistics"""
    try:
        from .storage import init_database, ContentRepository, TrendRepository
        from .models.content import Platform

        db_url = db or os.getenv("DATABASE_URL", "sqlite:///./data/content_trends.db")
        database = init_database(db_url)
        session = database.get_session()
        content_repo = ContentRepository(session)
        trend_repo = TrendRepository(session)

        click.echo("📊 Content Trends Analyzer Status\n")

        # Content statistics
        click.echo("Content Items (last 24 hours):")
        total_24h = 0
        for platform in Platform:
            count = content_repo.count_by_platform(platform, hours=24)
            if count > 0:
                total_24h += count
                click.echo(f"  {platform.value}: {count}")

        click.echo(f"\nTotal: {total_24h}")

        # Trend statistics
        active_trends = trend_repo.get_active(limit=1000)
        click.echo(f"\nActive Trends: {len(active_trends)}")

        if active_trends:
            click.echo("\nTop 5 Trends:")
            for trend in active_trends[:5]:
                click.echo(f"  - {trend.name} ({trend.metrics.mention_count} mentions)")

        session.close()
        database.close()

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


def main():
    """Main entry point"""
    cli()


if __name__ == '__main__':
    main()
