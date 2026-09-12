# Luso Hotel AI Production Guide

This package is a production candidate. Do not grant hotel clients access until the live tenant-isolation test and an appropriate load test pass in the deployed environment.

## 1. Install and test locally

```powershell
Copy-Item ".env.example" ".env"
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

Open `/api/health/live` and `/api/health/ready`. Both must return HTTP 200.

## 2. Apply the production database migration

Copy `app/sql/production_security.sql` into the Supabase SQL Editor and run it once. It is safe to rerun. The migration creates tenant-scoped dashboard and RAG functions plus query indexes.

## 3. Roles

Supported `hotel_users.role` values:

- `owner`: hotel owner
- `admin`: system administrator
- `manager`: hotel management
- `front_desk`: front-desk operations
- `staff`: general operations staff

Every authenticated user must have a `hotel_users` row. A user with memberships in multiple hotels must send `X-Hotel-ID`; a user cannot select a hotel for which they have no membership.

## 4. Live tenant-isolation gate

Create a second test hotel, create one test user for each hotel, and assign both users an allowed role. Set these temporary environment variables locally:

```powershell
$env:TEST_API_URL="http://127.0.0.1:8001"
$env:SUPABASE_PUBLISHABLE_KEY="YOUR_PUBLISHABLE_KEY"
$env:HOTEL_A_EMAIL="first-test-user@example.com"
$env:HOTEL_A_PASSWORD="TEMPORARY_PASSWORD_A"
$env:HOTEL_B_EMAIL="second-test-user@example.com"
$env:HOTEL_B_PASSWORD="TEMPORARY_PASSWORD_B"
.\.venv\Scripts\python.exe ".\scripts\live_tenant_isolation.py"
```

Expected: `LIVE TENANT ISOLATION: PASSED`. Remove the test users or rotate their passwords afterward. The script removes its temporary guest automatically.

## 5. GitHub

Before the first push:

```powershell
git status
git check-ignore .env
git grep -n -E "sb_secret_|service_role.*eyJ|sk-[A-Za-z0-9_-]{20,}"
```

The second command must print `.env`. The third command must return no credential values. If a secret was ever committed, rotate it; removing it from the latest commit is not sufficient.

Then initialize and push:

```powershell
git init
git add .
git commit -m "Production hardening for Luso Hotel AI"
git branch -M main
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

GitHub Actions runs static checks, tests, and a Docker build on each push and pull request.

## 6. Render deployment

Create a Render Web Service from the GitHub repository and choose Docker. Use `/api/health/ready` as the health-check path. Add the following environment variables in Render, never in GitHub source:

```text
APP_ENV=production
OPENAI_API_KEY=<secret>
OPENAI_MODEL=gpt-5
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_KEY=<server secret>
REDIS_URL=<Render Key Value internal URL>
ALLOWED_ORIGINS=https://YOUR_RENDER_DOMAIN
TRUSTED_HOSTS=YOUR_RENDER_HOSTNAME,YOUR_CUSTOM_DOMAIN
RATE_LIMIT_REQUESTS=120
RATE_LIMIT_WINDOW_SECONDS=60
MAX_PAGE_SIZE=200
WEB_CONCURRENCY=2
```

Use a paid service tier for client traffic. Configure autoscaling based on observed CPU/memory and latency rather than assuming a fixed user capacity.

## 7. Supabase production URLs

In Supabase Authentication URL Configuration, set Site URL to the exact HTTPS production address. Add only the exact production redirect URL(s) needed. Keep localhost only for development.

## 8. Load test

Use a dedicated test user and staging environment; do not load-test production during hotel operations.

```powershell
$env:LOAD_TEST_ACCESS_TOKEN="TEMPORARY_STAGING_ACCESS_TOKEN"
.\.venv\Scripts\locust.exe -f ".\loadtest\locustfile.py" --host "https://YOUR-STAGING-DOMAIN"
```

Open the Locust URL shown in the terminal. Increase users gradually (25, 100, 250, then higher). Monitor p95 latency, error rate, Supabase usage, OpenAI rate limits, CPU, and memory. Capacity is established by measurements, not by the configured worker count.

## 9. Release gate

All must pass:

- Unit/API tests
- Live tenant-isolation test
- Supabase RLS/security advisors reviewed
- Health and readiness checks
- No secrets in Git history
- Staging load test at expected concurrency
- Backup and restore procedure tested
- Monitoring and billing alerts enabled
- Hotel data-processing/privacy terms reviewed
- Separate production and staging credentials

## 10. PMS integration

Do not connect directly to an unknown PMS database. Obtain the PMS vendor, API documentation, sandbox credentials, supported webhooks, rate limits, and hotel authorization. Build a vendor adapter that maps reservations, guests, rooms, and folios into tenant-scoped records. If the PMS has no API, use an approved scheduled CSV export/import workflow rather than screen scraping or direct database access.
