# TaskBuddy

Personal Telegram bot for **tasks** and **notes**, filed into **Privat**,
**Arbeit**, or custom projects — with Eisenhower priorities **A–D**.

**Single-user · German UI · Python 3.11+ · SQLite locally**

## Features

- Paste text → new task (or `notiz: …` / `/note`)
- Detects Privat / Arbeit / project name; asks with buttons if unclear
- Create projects on the fly (`/project neu Name` or inline)
- Task priorities (sorted A→D):
  - **A** Wichtig & Dringend
  - **B** Dringend & Unwichtig
  - **C** Wichtig & Undringend
  - **D** Unwichtig & Undringend
- `/done ID` removes a finished task (soft-delete)
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
| `/note …` | New note |
| `/tasks [Projekt]` | Tasks sorted A→D |
| `/notes [Projekt]` | Notes |
| `/projects` | List projects |
| `/project neu Name` | Create project |
| `/done ID` | Complete/remove task |
| `/suche …` | Search |
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
