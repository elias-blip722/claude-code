import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging

from ..models.content import ContentItem
from ..models.trend import TrendItem
from ..models.config import OutputFormat, OutputConfig


class ReportGenerator:
    """Generate reports from collected data"""

    def __init__(self, config: OutputConfig, output_dir: str = "./reports"):
        self.config = config
        self.output_dir = output_dir
        self.logger = logging.getLogger(__name__)

        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_report(
        self,
        content_items: List[ContentItem],
        trends: List[TrendItem],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Generate reports in configured formats.

        Returns:
            Dictionary mapping format to output file path
        """
        output_files = {}

        # Prepare report data
        report_data = self._prepare_report_data(content_items, trends, metadata)

        # Generate in each configured format
        for format_type in self.config.formats:
            try:
                if format_type == OutputFormat.JSON:
                    filepath = self._generate_json(report_data)
                    output_files['json'] = filepath

                elif format_type == OutputFormat.CSV:
                    filepaths = self._generate_csv(report_data)
                    output_files['csv'] = filepaths

                elif format_type == OutputFormat.HTML:
                    filepath = self._generate_html(report_data)
                    output_files['html'] = filepath

            except Exception as e:
                self.logger.error(f"Error generating {format_type} report: {e}")

        return output_files

    def _prepare_report_data(
        self,
        content_items: List[ContentItem],
        trends: List[TrendItem],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Prepare data for reporting"""
        data = {
            "metadata": metadata or {},
            "generated_at": datetime.utcnow().isoformat(),
            "summary": self._generate_summary(content_items, trends),
            "trends": [trend.to_dict() for trend in trends],
            "content_items": [item.to_dict() for item in content_items],
        }

        return data

    def _generate_summary(
        self,
        content_items: List[ContentItem],
        trends: List[TrendItem]
    ) -> Dict[str, Any]:
        """Generate summary statistics"""
        from collections import Counter

        # Platform distribution
        platform_counts = Counter(item.platform.value for item in content_items)

        # Content type distribution
        content_type_counts = Counter(item.content_type.value for item in content_items)

        # Total engagement
        total_engagement = sum(
            item.engagement.likes + item.engagement.shares + item.engagement.comments
            for item in content_items
        )

        # Average engagement
        avg_engagement = total_engagement / len(content_items) if content_items else 0

        # Top hashtags
        all_hashtags = []
        for item in content_items:
            all_hashtags.extend(item.content.hashtags)
        top_hashtags = Counter(all_hashtags).most_common(10)

        # Sentiment distribution
        sentiment_counts = Counter()
        for item in content_items:
            if item.analysis and item.analysis.sentiment:
                sentiment_counts[item.analysis.sentiment.value] += 1

        return {
            "total_items": len(content_items),
            "total_trends": len(trends),
            "total_engagement": total_engagement,
            "average_engagement": avg_engagement,
            "platforms": dict(platform_counts),
            "content_types": dict(content_type_counts),
            "top_hashtags": [{"tag": tag, "count": count} for tag, count in top_hashtags],
            "sentiment_distribution": dict(sentiment_counts),
        }

    def _generate_json(self, data: Dict[str, Any]) -> str:
        """Generate JSON report"""
        import json

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"content_trends_report_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        self.logger.info(f"JSON report generated: {filepath}")
        return filepath

    def _generate_csv(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Generate CSV reports"""
        import csv

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        output_files = {}

        # Generate trends CSV
        trends_filename = f"trends_{timestamp}.csv"
        trends_filepath = os.path.join(self.output_dir, trends_filename)

        with open(trends_filepath, 'w', newline='', encoding='utf-8') as f:
            if data['trends']:
                writer = csv.DictWriter(f, fieldnames=self._get_trend_csv_fields())
                writer.writeheader()

                for trend in data['trends']:
                    row = self._flatten_trend_for_csv(trend)
                    writer.writerow(row)

        output_files['trends'] = trends_filepath

        # Generate content items CSV
        items_filename = f"content_items_{timestamp}.csv"
        items_filepath = os.path.join(self.output_dir, items_filename)

        with open(items_filepath, 'w', newline='', encoding='utf-8') as f:
            if data['content_items']:
                writer = csv.DictWriter(f, fieldnames=self._get_content_csv_fields())
                writer.writeheader()

                for item in data['content_items']:
                    row = self._flatten_content_for_csv(item)
                    writer.writerow(row)

        output_files['content'] = items_filepath

        self.logger.info(f"CSV reports generated: {output_files}")
        return output_files

    def _generate_html(self, data: Dict[str, Any]) -> str:
        """Generate HTML report"""
        from jinja2 import Template

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"content_trends_report_{timestamp}.html"
        filepath = os.path.join(self.output_dir, filename)

        template = self._get_html_template()
        html_content = template.render(data=data)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)

        self.logger.info(f"HTML report generated: {filepath}")
        return filepath

    def _get_trend_csv_fields(self) -> List[str]:
        """Get CSV field names for trends"""
        return [
            'id', 'name', 'type', 'detected_at', 'mention_count',
            'growth_rate', 'unique_authors', 'total_engagement',
            'velocity_score', 'platforms', 'keywords'
        ]

    def _get_content_csv_fields(self) -> List[str]:
        """Get CSV field names for content items"""
        return [
            'id', 'platform', 'content_type', 'url', 'created_at',
            'author_name', 'title', 'likes', 'shares', 'comments',
            'views', 'sentiment', 'relevance_score', 'hashtags'
        ]

    def _flatten_trend_for_csv(self, trend: Dict[str, Any]) -> Dict[str, str]:
        """Flatten trend data for CSV"""
        import json

        return {
            'id': trend['id'],
            'name': trend['name'],
            'type': trend['type'],
            'detected_at': trend['detected_at'],
            'mention_count': trend['metrics']['mention_count'],
            'growth_rate': trend['metrics']['growth_rate'],
            'unique_authors': trend['metrics']['unique_authors'],
            'total_engagement': trend['metrics']['total_engagement'],
            'velocity_score': trend['metrics']['velocity_score'],
            'platforms': json.dumps(trend['metrics']['platforms']),
            'keywords': ', '.join(trend.get('keywords', [])),
        }

    def _flatten_content_for_csv(self, item: Dict[str, Any]) -> Dict[str, str]:
        """Flatten content item for CSV"""
        return {
            'id': item['id'],
            'platform': item['platform'],
            'content_type': item['content_type'],
            'url': item['url'],
            'created_at': item['metadata']['created_at'],
            'author_name': item['author'].get('display_name', ''),
            'title': item['content'].get('title', '')[:100],
            'likes': item['engagement']['likes'],
            'shares': item['engagement']['shares'],
            'comments': item['engagement']['comments'],
            'views': item['engagement']['views'],
            'sentiment': item.get('analysis', {}).get('sentiment', ''),
            'relevance_score': item.get('analysis', {}).get('relevance_score', 0),
            'hashtags': ', '.join(item['content'].get('hashtags', [])),
        }

    def _get_html_template(self) -> Template:
        """Get HTML report template"""
        from jinja2 import Template

        template_str = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Content Trends Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }
        h1 { color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }
        h2 { color: #666; margin-top: 30px; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
        .stat-card { background: #f9f9f9; padding: 15px; border-radius: 5px; border-left: 4px solid #4CAF50; }
        .stat-card h3 { margin: 0; color: #666; font-size: 14px; }
        .stat-card p { margin: 5px 0 0 0; font-size: 24px; font-weight: bold; color: #333; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #4CAF50; color: white; }
        tr:hover { background-color: #f5f5f5; }
        .trend-name { font-weight: bold; color: #4CAF50; }
        .metric { color: #666; font-size: 0.9em; }
        .timestamp { color: #999; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Content Trends Analysis Report</h1>
        <p class="timestamp">Generated: {{ data.generated_at }}</p>

        <h2>Summary</h2>
        <div class="summary">
            <div class="stat-card">
                <h3>Total Items</h3>
                <p>{{ data.summary.total_items }}</p>
            </div>
            <div class="stat-card">
                <h3>Trends Detected</h3>
                <p>{{ data.summary.total_trends }}</p>
            </div>
            <div class="stat-card">
                <h3>Total Engagement</h3>
                <p>{{ "{:,}".format(data.summary.total_engagement) }}</p>
            </div>
            <div class="stat-card">
                <h3>Avg Engagement</h3>
                <p>{{ "%.1f"|format(data.summary.average_engagement) }}</p>
            </div>
        </div>

        <h2>Top Trends</h2>
        <table>
            <thead>
                <tr>
                    <th>Trend</th>
                    <th>Type</th>
                    <th>Mentions</th>
                    <th>Growth Rate</th>
                    <th>Engagement</th>
                </tr>
            </thead>
            <tbody>
                {% for trend in data.trends[:20] %}
                <tr>
                    <td class="trend-name">{{ trend.name }}</td>
                    <td>{{ trend.type }}</td>
                    <td>{{ trend.metrics.mention_count }}</td>
                    <td>{{ "%.2f"|format(trend.metrics.growth_rate) }}x</td>
                    <td>{{ "{:,}".format(trend.metrics.total_engagement) }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <h2>Platform Distribution</h2>
        <table>
            <thead>
                <tr>
                    <th>Platform</th>
                    <th>Items</th>
                    <th>Percentage</th>
                </tr>
            </thead>
            <tbody>
                {% for platform, count in data.summary.platforms.items() %}
                <tr>
                    <td>{{ platform }}</td>
                    <td>{{ count }}</td>
                    <td>{{ "%.1f"|format(count / data.summary.total_items * 100) }}%</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
        '''

        return Template(template_str)
