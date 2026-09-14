# TaskBuddy

Personal Telegram bot for **tasks**, filed into **Privat**, **Arbeit**, or
**Backlog** — with Eisenhower priorities **A–D**.

**Single-user · German UI · Python 3.11+ · SQLite locally**

## Features

- Paste text → new task
- Detects Privat / Arbeit / Backlog; asks with buttons if unclear
- Task list grouped by **project**, then A→D (Backlog has its own list)
- Filter A–D; Done buttons only after picking a priority (not on All)
- **Backlog** is for effortful work to do in a calmer life phase — not the same as D
- `/backlog` or the Backlog keyboard button shows parked tasks
- `/done ID` still completes a task
- `/clear` deletes all open active tasks (with confirmation)
- Optional Gemini for classification

## Quick start (local SQLite)

1. Create a bot with [@BotFather](https://t.me/BotFather) (**new token**, not LinkBuddy’s).
2. Install:

```powershell
cd C:\Users\Baxx\Projects\taskbuddy
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

3. Set in `.env`: `TELEGRAM_BOT_TOKEN`, `OWNER_USER_ID` (your Telegram id).
4. Run:

```powershell
python main.py
```

SQLite file: `taskbuddy.db` in the project root.

## Commands

| Command | Purpose |
|---------|---------|
| (free text) | New task + confirm flow |
| `/tasks [A\|B\|C\|D]` | Active tasks (Privat & Arbeit), grouped by project |
| `/backlog [A\|B\|C\|D]` | Backlog only |
| `/done ID` | Complete/remove a task |
| `/clear` | Delete all open active tasks (confirm) |
| `/search …` | Search |
| `/help` | Help |

## Tests

```powershell
pip install -r requirements-dev.txt
pytest
```

## Deploy

See **[docs/DEPLOY.md](docs/DEPLOY.md)** (Railway + Postgres).

**Run only one polling process per token.**

## License

MIT — see [LICENSE](LICENSE).
