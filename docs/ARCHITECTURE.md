# TaskBuddy Architecture

Single-user Telegram bot for tasks.

## Stack

- python-telegram-bot (polling)
- SQLAlchemy 2 async (SQLite locally, Postgres-ready)
- Optional Gemini for project/priority hints

## Domain

- **Project** — `private` / `work` / `backlog` (seed: Privat, Arbeit, Backlog)
- **Item** — `task` with priority A–D (`type=note` is leftover only and not shown)
- **Subtask** — checklist rows on a task (`subtasks` table); not listed as own tasks
- `Item.body` is the optional description/notes (shown indented with `-` under the title)
- Main task list is Privat & Arbeit only, grouped by project then A–D
- Backlog lists parked tasks separately
- Done tasks are soft-deleted (`deleted_at`) and listed/restored with `/undo` or `undo 12`
- Unique subtask names can be checked off with `done …`
- **Backlog** is a project for effortful work in a calmer phase — not priority D

## Flow

Text → parse (title / notes / `-` subtasks) → heuristic (+ optional Gemini) → confirm project/priority via inline buttons → save.

Lists are grouped by A–D. Open a task with `#12`. Complete with `done name`. Restore with `/undo` then `undo 12`.

## Layout

```
src/taskbuddy/
  bot/handlers/   capture, query, manage, common, router
  db/             models, repository, engine
  services/       classify, priority, formatting, gemini, intent
```
