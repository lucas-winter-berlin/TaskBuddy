# TaskBuddy

Personal Telegram bot for **tasks**, filed into **Privat**, **Arbeit**, or
**Backlog** — with Eisenhower priorities **A–D**.

**Single-user · Python 3.11+ · SQLite locally / Postgres on Railway**

## How to use

Type a task. Extra lines are notes; lines starting with `-` become subtasks.

| You type | What happens |
|----------|----------------|
| `Buy milk` | New task (confirm project/priority) |
| `#12` | Open that task with notes and subtasks |
| `edit Steuer` / `bearbeiten 12` | Same card, then change title/notes/prio/project |
| `done Steuer` / `erledigt …` / `fertig #12` | Complete the task |
| `undo` or `/undo` | List completed tasks |
| `undo 12` / `/undo 12` | Restore that task |
| Keyboard **Tasks** / **Backlog** / **Search** | Lists and search |

Filter A–D in the list to get Done buttons. `/clear` deletes all open active tasks (confirm). `/help`, `/menu`, `/settings` stay as slash commands.

**Backlog** is effortful work for a calmer phase — not the same as D.

Optional Gemini (env `GEMINI_API_KEY`) guesses project and priority; without a key, keywords only.

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
