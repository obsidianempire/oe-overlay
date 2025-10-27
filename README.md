# OE Overlay REST Service

FastAPI backend powering the overlay. It authenticates players via Discord, backs the crafting/event workflows with Postgres, and exposes the REST endpoints consumed by the desktop toolbar.

## Highlights
- Discord OAuth2 (identify + guilds.members.read) with guild/role enforcement.
- JWT issuance for the overlay client; /auth/me reports profile/permission info.
- Postgres models for crafting requests, crafting assignments, events, event attendees, and alert lookups.
- Render-ready configuration (managed Postgres + Python web service).
- Automatic schema creation on startup for the starter tables.

## Project Layout
`
server/
  app/
    auth.py          # Discord OAuth, JWT helpers, /auth routes
    config.py        # Environment-driven settings
    database.py      # Async SQLAlchemy engine/session helpers
    main.py          # FastAPI application entry point
    models.py        # SQLAlchemy models
    routers/
      alerts.py      # /alerts endpoints
      crafting.py    # /crafting endpoints
      data.py        # legacy overlay endpoints (events/roster/attendance)
      events.py      # /events endpoints
    schemas.py       # Pydantic response/request schemas
  requirements.txt
  README.md
`

## Environment Variables
| Variable | Description |
|----------|-------------|
| DATABASE_URL | Postgres DSN (postgresql+psycopg_async://user:pass@host:port/db) |
| DISCORD_CLIENT_ID | Discord OAuth2 client ID |
| DISCORD_CLIENT_SECRET | Discord OAuth2 client secret |
| DISCORD_REDIRECT_URI | OAuth redirect URI (e.g. https://<service>.onrender.com/api/auth/callback) |
| DISCORD_GUILD_IDS | Comma-separated guild IDs allowed to use the API (defaults to OE guild) |
| DISCORD_EVENT_ROLE_IDS | Optional comma-separated role IDs allowed to create events |
| JWT_SECRET_KEY | Secret key for signing JWTs |
| JWT_ALGORITHM | Optional JWT signing algorithm (default HS256) |
| JWT_EXPIRE_MINUTES | Optional JWT lifetime in minutes (default 60) |
| API_BASE_PATH | Optional API base prefix (default /api) |
| CORS_ALLOW_ORIGINS | Optional comma-separated origins for browser clients |
| ALERT_LEAD_MINUTES | Minutes before start time an event should raise an alert badge (default 15) |
| ENVIRONMENT | Optional environment label (development, production, …) |

> Create a server/.env file for local development and populate the variables above.

## Local Development
1. **Virtual environment**
   `ash
   cd server
   python -m venv .venv
   source .venv/bin/activate  # Windows: .\.venv\Scripts\Activate.ps1
   `
2. **Install dependencies**
   `ash
   pip install -r requirements.txt
   `
3. **Create .env**
   `dotenv
   DATABASE_URL=postgresql+psycopg_async://postgres:postgres@localhost:5432/oe_overlay
   DISCORD_CLIENT_ID=123456789012345678
   DISCORD_CLIENT_SECRET=super-secret
   DISCORD_REDIRECT_URI=http://localhost:8000/api/auth/callback
   DISCORD_GUILD_IDS=123456789012345678
   DISCORD_EVENT_ROLE_IDS=234567890123456789
   JWT_SECRET_KEY=generate_a_long_random_value
   `
4. **Run Postgres (Docker example)**
   `ash
   docker run --name oe-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 -d postgres:15
   `
5. **Start API**
   `ash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   `
6. **Docs & Auth**
   - Docs: http://localhost:8000/docs
   - Kick off OAuth: http://localhost:8000/api/auth/login
   - Callback returns JSON body with ccess_token / expires_in for the desktop overlay.

## Render Deployment
1. Provision a Postgres instance on Render.
2. Create a new Python web service pointing to this repo.
   - Build command: pip install -r server/requirements.txt
   - Start command: uvicorn app.main:app --host 0.0.0.0 --port 10000
3. Configure environment variables in the service dashboard (see table above). Remember to change the database URL prefix to postgresql+psycopg_async:// if you copy Render’s default string.
4. Set the Discord redirect URI in the developer portal to https://<service>.onrender.com/api/auth/callback.
5. Deploy. On first boot the API creates the tables automatically.

## REST Endpoints Used by the Overlay
- POST /api/auth/callback – exchanges OAuth code for JWT.
- GET /api/auth/me – returns user profile, guild roles, and config (used for event permissions/alert lead time).
- GET /api/crafting/requests, POST /api/crafting/requests, POST /api/crafting/requests/{id}/accept, POST /api/crafting/requests/{id}/complete, POST /api/crafting/requests/{id}/cancel
- GET /api/events, POST /api/events, POST /api/events/{id}/join, POST /api/events/{id}/leave, GET /api/events/{id}/attendees
- GET /api/alerts

Legacy endpoints under /api/overlay/* remain available for compatibility (events/roster/attendance) but are no longer used by the latest overlay UI.

## Database Schema (Starter)
- **craft_requests** – pending crafting jobs submitted by players.
- **craft_assignments** – crafter claims with meet location/time and completion status.
- **events** – scheduled events (creator, start time, optional required role IDs).
- **event_attendees** – RSVP list per event.
- **attendance_records** / **roster_members** – legacy data surfaced by the previous overlay tabs (optional).

## Discord OAuth Flow Recap
1. Overlay opens /api/auth/login ? Discord authorization screen.
2. Discord redirects to /api/auth/callback?code=... after consent.
3. Service exchanges the code, validates guild membership (and optionally roles).
4. JWT returned to the overlay, which includes guild/role info and expiration.
5. Overlay stores the JWT and attaches it as Authorization: Bearer <token> on subsequent calls.

## Extending Further
- Add admin endpoints for managing crafting requests/events from a web dashboard.
- Integrate WebSockets/SSE for push notifications.
- Introduce proper migrations (Alembic) as the schema evolves.
- Rotate JWT secrets periodically or swap to asymmetric signing.

Happy hacking!
