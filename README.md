# OE Overlay REST Service

A FastAPI backend that powers the overlay UI. It enforces Discord-based authentication, stores
overlay data in Postgres, and serves the JSON endpoints consumed by the desktop overlay.

## Features

- Discord OAuth2 login with guild membership enforcement (only members of **Obsidian Empire**)
- JWT bearer tokens for the overlay to call authenticated endpoints
- Postgres-backed models for events, roster members, and attendance records
- Render-ready configuration (web service + managed Postgres)
- Automatic schema creation on startup (no migrations required for the starter schema)

## Project Structure

```
server/
  app/
    auth.py           # Discord OAuth2, JWT helpers, auth dependency
    config.py         # Settings via environment / .env
    database.py       # Async SQLAlchemy engine/session
    main.py           # FastAPI app entrypoint
    models.py         # SQLAlchemy models
    routers/
      data.py         # /overlay REST endpoints
    schemas.py        # Pydantic schemas
  requirements.txt
  README.md           # This file
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Postgres connection string (`postgresql+asyncpg://user:pass@host:port/db`) |
| `DISCORD_CLIENT_ID` | Discord OAuth2 client ID |
| `DISCORD_CLIENT_SECRET` | Discord OAuth2 client secret |
| `DISCORD_REDIRECT_URI` | OAuth redirect URI registered with Discord (e.g. `https://<service>.onrender.com/api/auth/callback`) |
| `DISCORD_GUILD_IDS` | Comma-separated list of Discord guild IDs allowed to use the API (include the Obsidian Empire guild ID) |
| `JWT_SECRET_KEY` | Secret used to sign JWTs (generate a strong random string) |
| `JWT_ALGORITHM` | Optional signing algorithm (defaults to `HS256`) |
| `JWT_EXPIRE_MINUTES` | Optional JWT lifetime (defaults to `60`) |
| `API_BASE_PATH` | Optional API base prefix (defaults to `/api`) |
| `CORS_ALLOW_ORIGINS` | Optional comma-separated list of origins allowed for browser requests |
| `ENVIRONMENT` | Optional environment label (`development`, `production`, etc.) |

> When running locally you can create a `.env` file at `server/.env` and populate the variables above.

## Local Development

1. **Create & activate a virtual environment**
   ```bash
   cd server
   python -m venv .venv
   source .venv/bin/activate  # Windows PowerShell: .\.venv\Scripts\Activate.ps1
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create the `.env` file**
   ```dotenv
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/oe_overlay
   DISCORD_CLIENT_ID=123456789012345678
   DISCORD_CLIENT_SECRET=super-secret
   DISCORD_REDIRECT_URI=http://localhost:8000/api/auth/callback
   DISCORD_GUILD_IDS=123456789012345678
   JWT_SECRET_KEY=generate_a_long_random_value
   ```

4. **Run Postgres locally** (any method you prefer, e.g. Docker):
   ```bash
   docker run --name oe-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:15
   ```

5. **Start the API**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Visit docs / perform OAuth**
   - API docs: `http://localhost:8000/docs`
   - Initiate Discord login: `http://localhost:8000/api/auth/login`

   After completing the OAuth flow, the callback endpoint returns a JSON body with a JWT:
   ```json
   {
     "access_token": "xxxx.yyyy.zzzz",
     "token_type": "bearer",
     "expires_in": 3600
   }
   ```

7. **Call the overlay endpoints**
   ```bash
   curl -H "Authorization: Bearer <token>" http://localhost:8000/api/overlay/events
   ```

## Deploying on Render

1. **Create a Render Postgres instance**
   - Dashboard → New → PostgreSQL
   - Note the `Internal Database URL`; Render exposes it as `DATABASE_URL` by default

2. **Create a Web Service**
   - Dashboard → New → Web Service
   - Select your GitHub repo (containing this project)
   - Build command: `pip install -r server/requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port 10000`
   - Environment: `Python`

3. **Configure environment variables**
   - `DATABASE_URL`: use the Render Postgres internal connection string but ensure it begins with `postgresql+asyncpg://`
   - `DISCORD_CLIENT_ID` / `DISCORD_CLIENT_SECRET`: from your Discord developer application
   - `DISCORD_REDIRECT_URI`: `https://<render-service>.onrender.com/api/auth/callback`
   - `DISCORD_GUILD_IDS`: the numeric guild ID for Obsidian Empire (and any others you want to allow)
   - `JWT_SECRET_KEY`: random secret string
   - Optional: `CORS_ALLOW_ORIGINS` (comma-separated origins that can call the API from a browser)

4. **Deploy**
   - Render automatically deploys on push; you can also trigger manual deploys
   - On first boot, the app auto-creates the required tables

5. **Update Discord redirect**
   - In [Discord Developer Portal](https://discord.com/developers/applications), open your application
   - OAuth2 → Redirects → add the Render callback URL

## Discord OAuth Flow Summary

1. Client hits `/api/auth/login` (or constructs the Discord OAuth URL manually).
2. After user authorises the app, Discord redirects to `/api/auth/callback?code=...`.
3. The service verifies the user belongs to one of `DISCORD_GUILD_IDS`.
4. A JWT is returned; the overlay includes this token in the `Authorization: Bearer <token>` header.
5. `/api/overlay/*` endpoints return data only when authorised.

## Database Notes

The starter schema stores:

- `events`: title, description, timezone-aware start time
- `roster_members`: guild roster information (name, role, combat power, etc.)
- `attendance_records`: event attendance with a JSON list of attendee names

Feel free to extend or normalize the schema to match your needs (e.g. add admin endpoints, audit logs, etc.).

## Extending the Service

- Add authenticated `POST/PUT/DELETE` routes for managing data
- Integrate caching for the read endpoints if traffic grows
- Swap JWT signing for a dedicated auth service or rotate secrets periodically
- Introduce Alembic migrations as the schema evolves

---

Questions or enhancements? Update the repository, redeploy on Render, and refresh the overlay client configuration to point at the new API base URL.
