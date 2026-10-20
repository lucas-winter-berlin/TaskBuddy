# app-task-buddy

Public. License: MIT.

Personal Telegram bot for tasks, notes, and projects. Single user. Python 3.11+. SQLite locally, Postgres on Railway.

## Start

```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python main.py
```

Set `TELEGRAM_BOT_TOKEN` and `OWNER_USER_ID` in `.env`. SQLite file: `taskbuddy.db` in the project root.

## Commands

```
pip install -r requirements-dev.txt
pytest
```

## Secrets

`.env` from `.env.example`. Never commit the bot token. One polling process per token.

## Docs

| Doc | Content |
|-----|---------|
| [docs/README.md](docs/README.md) | Index |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | How the bot is built |
| [docs/DEPLOY.md](docs/DEPLOY.md) | Railway and Postgres |
