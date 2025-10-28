# Content Trends Analyzer

A powerful multi-platform content monitoring and trend analysis tool that helps you track social media trends, analyze content patterns, and generate actionable insights.

## Features

### ✅ Currently Working

- **YouTube Integration** - Full support for YouTube Data API v3
  - Search videos by keywords
  - Monitor specific channels
  - Filter by views, likes, duration
  - Extract comprehensive metadata

- **RSS Feed Monitoring** - Monitor blogs and news sites
  - Support for any standard RSS/Atom feed
  - Keyword filtering
  - Automatic deduplication

- **Data Processing Pipeline**
  - Content deduplication using fingerprinting
  - Text normalization and cleaning
  - Keyword extraction
  - Spam detection

- **Trend Detection**
  - Hashtag trend analysis
  - Keyword trend detection
  - Topic clustering
  - Growth rate calculation
  - Velocity scoring

- **Sentiment Analysis**
  - TextBlob integration
  - Fallback keyword-based analysis
  - Sentiment scoring (-1 to 1)

- **Reporting & Exports**
  - JSON format (complete data)
  - CSV format (trends + content items)
  - HTML reports with visualizations
  - Summary statistics

- **CLI Interface**
  - Easy-to-use commands
  - Configuration management
  - Status monitoring

### 🔜 Ready for Integration

- **Twitter/X** - Framework ready, awaiting API credentials
- **Meta Content Library** - Framework ready, awaiting access approval

## Installation

### Prerequisites

- Python 3.11 or higher
- Google API Key (for YouTube)
- (Optional) Twitter API credentials
- (Optional) Meta Content Library access

### Setup

1. **Clone or navigate to the project directory**

```bash
cd content-trends-analyzer
```

2. **Create a virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure environment variables**

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

```env
# Required for YouTube
GOOGLE_API_KEY=your_google_api_key_here
YOUTUBE_API_KEY=your_youtube_api_key_here

# Optional: Twitter/X (add when available)
TWITTER_BEARER_TOKEN=your_bearer_token_here

# Optional: Meta Content Library (add when available)
META_ACCESS_TOKEN=your_access_token_here

# Database
DATABASE_URL=sqlite:///./data/content_trends.db
```

5. **Create a configuration file**

```bash
python -m src.cli init-config --name "My Analysis" --output config/my_config.yaml
```

Edit `config/my_config.yaml` to customize your monitoring setup.

## Quick Start

### 1. Collect Content

```bash
python -m src.cli collect --config config/my_config.yaml
```

This will:
- Fetch content from YouTube based on your search terms
- Parse RSS feeds for matching articles
- Store everything in the database
- Skip duplicates automatically

### 2. Analyze and Generate Reports

```bash
python -m src.cli analyze --config config/my_config.yaml --hours 24
```

This will:
- Analyze content from the last 24 hours
- Detect trending hashtags, keywords, and topics
- Perform sentiment analysis
- Generate reports in JSON, CSV, and HTML formats

### 3. Run Full Pipeline

```bash
python -m src.cli run --config config/my_config.yaml
```

This combines collect + analyze into one command.

### 4. Check Status

```bash
python -m src.cli status
```

Shows:
- Content items collected (by platform)
- Active trends
- Database statistics

## Configuration

The configuration file (`config/my_config.yaml`) controls all aspects of monitoring:

### YouTube Configuration

```yaml
youtube:
  enabled: true
  search_terms:
    - "artificial intelligence 2025"
    - "machine learning tutorial"
  channels:
    - "CHANNEL_ID_HERE"
  min_views: 1000
  min_likes: 50
  max_duration: 3600  # 1 hour
  max_results: 50
```

### RSS Feeds Configuration

```yaml
rss_feeds:
  enabled: true
  feeds:
    - "https://techcrunch.com/feed/"
    - "https://www.theverge.com/rss/index.xml"
  keywords:
    - "AI"
    - "machine learning"
```

### Trend Detection Configuration

```yaml
analysis:
  trend_detection:
    enabled: true
    min_mentions: 5        # Minimum mentions to be a trend
    time_window: "24h"
    growth_threshold: 1.5  # 1.5x growth = trending
```

See `config/example_config.yaml` for a complete example.

## Getting API Credentials

### YouTube API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable YouTube Data API v3
4. Create credentials (API Key)
5. Add the API key to your `.env` file

**Cost**: Free tier includes 10,000 quota units per day (enough for ~3,000 video searches)

### Twitter/X API (Optional)

1. Go to [Twitter Developer Portal](https://developer.twitter.com/)
2. Apply for API access
3. Create a new app
4. Generate API keys and bearer token
5. Add credentials to `.env` file

**Note**: Twitter API access requires approval and may have costs associated.

### Meta Content Library (Optional)

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Apply for Content Library access
3. Create an app
4. Once approved, generate access token
5. Add credentials to `.env` file

**Note**: Meta Content Library is for researchers and requires application approval.

## Project Structure

```
content-trends-analyzer/
├── src/
│   ├── collectors/       # Data collectors for each platform
│   │   ├── youtube.py    # ✅ Working
│   │   ├── twitter.py    # 🔜 Framework ready
│   │   ├── meta.py       # 🔜 Framework ready
│   │   └── rss.py        # ✅ Working
│   ├── models/           # Data models (Pydantic)
│   │   ├── content.py    # Content item model
│   │   ├── trend.py      # Trend model
│   │   └── config.py     # Configuration model
│   ├── storage/          # Database layer (SQLAlchemy)
│   │   ├── database.py   # Database models
│   │   └── repository.py # Data access layer
│   ├── analysis/         # Analysis engines
│   │   ├── processor.py      # Content processing
│   │   ├── trend_detector.py # Trend detection
│   │   └── sentiment.py      # Sentiment analysis
│   ├── reporting/        # Report generation
│   │   └── generator.py  # Multi-format reports
│   └── cli.py            # Command-line interface
├── config/               # Configuration files
│   └── example_config.yaml
├── data/                 # Database storage (auto-created)
├── reports/              # Generated reports (auto-created)
├── requirements.txt      # Python dependencies
├── pyproject.toml        # Project metadata
└── README.md             # This file
```

## Usage Examples

### Example 1: Monitor AI News

```yaml
# config/ai_news.yaml
monitoring_config:
  name: "AI News Monitoring"
  sources:
    youtube:
      enabled: true
      search_terms:
        - "AI news today"
        - "artificial intelligence breakthrough"
      min_views: 5000
    rss_feeds:
      enabled: true
      feeds:
        - "https://techcrunch.com/feed/"
        - "https://www.theverge.com/rss/index.xml"
      keywords:
        - "AI"
        - "artificial intelligence"
```

```bash
python -m src.cli run --config config/ai_news.yaml
```

### Example 2: Monitor Specific YouTube Channels

```yaml
youtube:
  enabled: true
  channels:
    - "UCXuqSBlHAE6Xw-yeJA0Tunw"  # Linus Tech Tips
    - "UC6nSFpj9HTCZ5t-N3Rm3-HA"  # Vsauce
  min_views: 10000
  max_results: 20
```

### Example 3: Keyword-Focused Analysis

```yaml
youtube:
  enabled: true
  search_terms:
    - "Python tutorial 2025"
    - "web development"
  min_views: 1000
rss_feeds:
  enabled: true
  keywords:
    - "Python"
    - "JavaScript"
    - "programming"
```

## Output Reports

### JSON Report

Complete data export with all fields:
```json
{
  "metadata": {},
  "generated_at": "2025-10-28T12:00:00",
  "summary": {
    "total_items": 150,
    "total_trends": 12,
    "total_engagement": 50000
  },
  "trends": [...],
  "content_items": [...]
}
```

### CSV Report

Two files generated:
- `trends_YYYYMMDD_HHMMSS.csv` - Trend data
- `content_items_YYYYMMDD_HHMMSS.csv` - Content data

Perfect for Excel, Google Sheets, or data analysis tools.

### HTML Report

Beautiful, interactive report with:
- Summary statistics
- Top trends table
- Platform distribution
- Engagement metrics
- Visualizations

Open in any web browser.

## Advanced Usage

### Custom Database Location

```bash
python -m src.cli collect --config config/my_config.yaml --db sqlite:///./custom/path/db.sqlite
```

### Analyze Different Time Ranges

```bash
# Last 12 hours
python -m src.cli analyze --config config/my_config.yaml --hours 12

# Last 7 days
python -m src.cli analyze --config config/my_config.yaml --hours 168
```

### Custom Output Directory

```bash
python -m src.cli run --config config/my_config.yaml --output ./my_reports/
```

## Troubleshooting

### "YouTube API key not provided"

Make sure you've:
1. Created a `.env` file
2. Added `GOOGLE_API_KEY=your_key_here`
3. The key is valid and YouTube Data API v3 is enabled

### "No content to analyze"

This means no content was collected. Check:
1. Your search terms are returning results
2. Your filters aren't too restrictive
3. You've run the `collect` command first

### "Rate limit exceeded"

YouTube API has daily quotas. Solutions:
1. Reduce `max_results` in config
2. Increase collection interval
3. Request quota increase from Google

### Database locked errors

If using SQLite, avoid running multiple collection processes simultaneously.

## Enabling Twitter/X Integration

Once you have Twitter API credentials:

1. Add to `.env`:
```env
TWITTER_BEARER_TOKEN=your_bearer_token_here
TWITTER_API_KEY=your_api_key_here
TWITTER_API_SECRET=your_api_secret_here
```

2. In `src/collectors/twitter.py`, uncomment the tweepy import and initialization code

3. Enable in config:
```yaml
twitter:
  enabled: true
  keywords:
    - "your keywords"
```

4. Run collection:
```bash
python -m src.cli collect --config config/my_config.yaml
```

## Enabling Meta Content Library

Once you have Meta Content Library access:

1. Add to `.env`:
```env
META_ACCESS_TOKEN=your_access_token_here
META_APP_ID=your_app_id_here
```

2. Review API documentation: https://developers.facebook.com/docs/content-library

3. Implement the API calls in `src/collectors/meta.py` (framework is ready)

4. Enable in config:
```yaml
meta:
  enabled: true
  keywords:
    - "your keywords"
```

## Roadmap

### Short Term
- [x] YouTube collector
- [x] RSS feed collector
- [x] Trend detection
- [x] Sentiment analysis
- [x] Multi-format reporting
- [ ] Scheduling system (cron-like)
- [ ] Twitter/X integration
- [ ] Meta Content Library integration

### Long Term
- [ ] Reddit integration
- [ ] Discord monitoring
- [ ] Real-time streaming
- [ ] Machine learning for trend prediction
- [ ] Web dashboard (React/Vue)
- [ ] Advanced NLP (entity recognition)
- [ ] Image/video content analysis
- [ ] Webhook notifications
- [ ] Multi-user support

## Contributing

Contributions are welcome! Areas for improvement:

- Additional platform collectors
- Better trend detection algorithms
- Enhanced sentiment analysis
- Performance optimizations
- Documentation improvements
- Bug fixes

## License

MIT License - see LICENSE file for details.

## Support

For issues, questions, or feature requests, please:
1. Check the troubleshooting section
2. Review configuration examples
3. Check API documentation for your platform
4. Open an issue with detailed information

## Acknowledgments

- YouTube Data API v3
- TextBlob for sentiment analysis
- SQLAlchemy for database management
- Click for CLI interface
- Pydantic for data validation

---

**Built with Claude Code** - An AI-assisted development tool by Anthropic
