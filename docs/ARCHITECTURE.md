# TaskBuddy Architecture

Single-user Telegram bot for tasks and notes.

## Stack

- python-telegram-bot (polling)
- SQLAlchemy 2 async (SQLite locally, Postgres-ready)
- Optional Gemini for project/priority hints

## Domain

- **Project** — `private` / `work` / `custom` (seed: Privat, Arbeit)
- **Item** — `task` (priority A–D) or `note` (no priority)
- Done tasks are soft-deleted (`deleted_at`)

## Flow

Text → parse type → heuristic (+ optional Gemini) → confirm project/priority via inline buttons → save.

## Layout

```
src/taskbuddy/
  bot/handlers/   capture, query, manage, common, router
  db/             models, repository, engine
  services/       classify, priority, formatting, gemini
```
