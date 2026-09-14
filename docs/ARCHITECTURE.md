# TaskBuddy Architecture

Single-user Telegram bot for tasks.

## Stack

- python-telegram-bot (polling)
- SQLAlchemy 2 async (SQLite locally, Postgres-ready)
- Optional Gemini for project/priority hints

## Domain

- **Project** — `private` / `work` / `backlog` (seed: Privat, Arbeit, Backlog). Leftover `custom` projects from v1 can still be listed/deleted.
- **Item** — `task` with priority A–D (`type=note` is leftover only and not shown)
- Main `/tasks` list is Privat & Arbeit only, grouped by project then A–D
- `/backlog` lists backlog tasks separately
- Done tasks are soft-deleted (`deleted_at`)
- **Backlog** is a project for effortful work in a calmer phase — not priority D

## Flow

Text → parse → heuristic (+ optional Gemini) → confirm project/priority via inline buttons → save.

Task list is grouped by A–D, filterable, with per-item Done buttons and `/clear`.

## Layout

```
src/taskbuddy/
  bot/handlers/   capture, query, manage, common, router
  db/             models, repository, engine
  services/       classify, priority, formatting, gemini
```
