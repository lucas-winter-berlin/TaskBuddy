# Deploy TaskBuddy on Railway

Persistent hosting with PostgreSQL (Railway’s filesystem is ephemeral — don’t rely on SQLite there).

## Dashboard

1. Open [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
2. Select this repo
3. **New** → **Database** → **PostgreSQL**
4. On the bot service → **Variables**:
   - `DATABASE_URL` = reference `${{Postgres.DATABASE_URL}}`
   - `TELEGRAM_BOT_TOKEN`
   - `OWNER_USER_ID`
   - optional: `GEMINI_API_KEY`, `GEMINI_MODEL`, `BOT_TIMEZONE=Europe/Berlin`
5. Deploy → logs should show `Bot @… ist bereit`
6. **Stop the local** `python main.py` (one polling process per token)

## CLI

```powershell
npm i -g @railway/cli
railway login
cd C:\Users\Baxx\Projects\taskbuddy
railway init --name TaskBuddy
railway add --database postgres
railway add --repo <you>/TaskBuddy --branch main --service taskbuddy
railway variable set TELEGRAM_BOT_TOKEN=... OWNER_USER_ID=... --service taskbuddy
# Wire DATABASE_URL as Postgres reference in the dashboard if needed
railway redeploy --service taskbuddy -y
```

Start command comes from `railway.toml`: `python main.py`.
