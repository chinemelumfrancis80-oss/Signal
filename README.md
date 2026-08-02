# SIGNAL — Personal Information Intelligence

This is a real runnable Flask application, not a static mockup.

## What it does
- Live RSS ingestion from configurable public feeds
- Automatic refresh in the background
- Source-first article feed
- Search across stored current + historical articles
- Topic pages
- Follow topics
- Save articles
- Timeline view
- Future items can be marked as planned/announced/forecast rather than fact
- Optional AI summary/explanation layer
- Responsive desktop + mobile UI
- SQLite persistence
- PWA install shell

## Run
1. Install Python 3.10+.
2. Create a virtual environment.
3. `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and set SECRET_KEY.
5. `python run.py`
6. Open http://127.0.0.1:5000

The app will create `signal.db` automatically and ingest its configured feeds.

## Live data
Feeds are configured in `app.py` under `DEFAULT_FEEDS`. Add or replace feeds with sources you are authorized to ingest. RSS metadata is stored locally; opening an article takes the user to the publisher's canonical page.

## AI
Set OPENAI_API_KEY and optionally OPENAI_MODEL to enable the optional AI endpoints. The OpenAI Python package is included in requirements.txt. The app keeps original-source links primary and labels AI-generated content.

## Production deployment
For public deployment, use a production WSGI server/reverse proxy, HTTPS, a persistent database, authentication, rate limiting, source-specific licensing/terms compliance, a job queue, and observability. The included scheduler is suitable for a single-instance deployment; larger deployments should move ingestion to a worker queue.


## Before public launch
This package is runnable, but a public production service still needs:
- deployment on a persistent server/cloud host
- HTTPS and a production WSGI server
- user accounts/authentication if personal sync is required
- production database/backups
- source-by-source feed verification and licensing/terms review
- a larger source catalogue and source health monitoring
- robust historical indexing and pagination
- push/email notifications
- stronger duplicate/event clustering
- production-grade AI safety, cost controls and rate limits
- monitoring, logging and error alerts
