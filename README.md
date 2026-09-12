# Luso Hotel AI

Tenant-aware AI concierge and hotel operations command center built with FastAPI, Supabase, pgvector, and OpenAI.

## Local start

1. Copy `.env.example` to `.env` and enter development credentials.
2. Run `python -m pip install -r requirements-dev.txt`.
3. Run the SQL files in `app/sql` using the Supabase SQL Editor.
4. Start with `python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload`.
5. Open `http://127.0.0.1:8001/dashboard`.

Never commit `.env`, server-side Supabase keys, OpenAI keys, passwords, or access tokens.

See `PRODUCTION-GUIDE.md` for the release procedure.
