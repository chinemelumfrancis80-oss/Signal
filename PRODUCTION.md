# Signal production launch

## What is included
- Real Flask backend
- SQLite persistence
- Background RSS ingestion
- Search, topics, timeline, saved and following
- Optional OpenAI summaries
- PWA shell
- Dockerfile + docker compose
- Gunicorn production server
- Health endpoint: `/health`
- Source endpoint: `/api/sources`

## Local
`pip install -r requirements.txt`
`python run.py`

## Docker
1. Copy `.env.example` to `.env`.
2. Set a strong SECRET_KEY.
3. Add authorized RSS sources in `app.py`.
4. Run `docker compose up --build -d`.
5. Open `http://localhost:8000`.

## What cannot be completed inside this chat
A public internet deployment requires an external hosting account/domain/DNS and any credentials required by the chosen news/API providers. Those are intentionally not invented or embedded.

## For the final public service
Use a managed PostgreSQL database, Redis/job queue for ingestion, object storage for media, HTTPS, authentication, rate limiting, structured logging, monitoring, backups, source-specific licensing/terms review, and a separate worker process. Keep original publisher URLs as the authoritative reading destination.
