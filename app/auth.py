import datetime as dt
from typing import Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from .config import get_settings
from .schemas import DiscordUser, Token, UserInfo


router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()
security = HTTPBearer(auto_error=False)

DISCORD_API_BASE = "https://discord.com/api"


class AuthenticatedUser(BaseModel):
    id: str
    username: str
    discriminator: str
    guild_ids: List[int]
    guild_roles: Dict[str, List[str]] = {}
    can_create_events: bool = False


def create_access_token(user: AuthenticatedUser) -> Token:
    expires_delta = dt.timedelta(minutes=settings.jwt_expire_minutes)
    expire = dt.datetime.now(dt.timezone.utc) + expires_delta
    payload = {
        "sub": user.id,
        "username": user.username,
        "discriminator": user.discriminator,
        "guild_ids": user.guild_ids,
        "guild_roles": user.guild_roles,
        "can_create_events": user.can_create_events,
        "exp": expire,
        "iss": "oe-overlay-service",
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return Token(access_token=token, expires_in=int(expires_delta.total_seconds()))


@router.get("/login", response_model=None, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
async def discord_login():
    """
    Redirect the caller to Discord OAuth2 authorisation page.

    Useful when a browser-based admin panel is used. The overlay can
    instead initiate the OAuth flow directly and call `/auth/callback`.
    """

    scope = "identify guilds guilds.members.read"
    redirect = (
        f"{DISCORD_API_BASE}/oauth2/authorize?"
        f"response_type=code&client_id={settings.discord_client_id}"
        f"&scope={scope.replace(' ', '%20')}"
        f"&redirect_uri={settings.discord_redirect_uri}"
        "&prompt=consent"
    )
    return Response(status_code=status.HTTP_307_TEMPORARY_REDIRECT, headers={"Location": redirect})


@router.api_route("/callback", methods=["POST", "GET"], response_model=Token)
async def discord_callback(code: str):
    """
    Exchange the Discord OAuth2 code for an access token and mint a JWT
    if the user belongs to one of the allowed guilds.
    """

    token_data = await _exchange_code_for_token(code)
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Discord token exchange failed.")

    discord_user = await _fetch_current_user(access_token)
    guild_ids = await _fetch_guild_ids(access_token)

    allowed = [gid for gid in guild_ids if gid in settings.discord_allowed_guild_ids]
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not part of an authorised guild.")

    guild_roles = await _fetch_member_roles(access_token, allowed)
    can_create_events = False
    if settings.discord_event_role_ids:
        for roles in guild_roles.values():
            if any(role_id in settings.discord_event_role_ids for role_id in roles):
                can_create_events = True
                break
    else:
        can_create_events = True

    user = AuthenticatedUser(
        id=discord_user.id,
        username=discord_user.username,
        discriminator=discord_user.discriminator,
        guild_ids=allowed,
        guild_roles=guild_roles,
        can_create_events=can_create_events,
    )
    return create_access_token(user)


async def _exchange_code_for_token(code: str) -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{DISCORD_API_BASE}/oauth2/token",
            data={
                "client_id": settings.discord_client_id,
                "client_secret": settings.discord_client_secret,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": str(settings.discord_redirect_uri),
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to obtain Discord token.")
    return response.json()


async def _fetch_current_user(access_token: str) -> DiscordUser:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{DISCORD_API_BASE}/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not fetch Discord user.")
    return DiscordUser.parse_obj(resp.json())


async def _fetch_guild_ids(access_token: str) -> list[int]:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{DISCORD_API_BASE}/users/@me/guilds",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not fetch guild membership.")
    guilds = resp.json()
    return [int(guild["id"]) for guild in guilds]


async def _fetch_member_roles(access_token: str, guild_ids: List[int]) -> Dict[str, List[str]]:
    guild_roles: Dict[str, List[str]] = {}
    if not guild_ids:
        return guild_roles
    async with httpx.AsyncClient(timeout=10) as client:
        for gid in guild_ids:
            resp = await client.get(
                f"{DISCORD_API_BASE}/users/@me/guilds/{gid}/member",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                roles = data.get("roles", [])
                guild_roles[str(gid)] = [str(role) for role in roles]
    return guild_roles


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> AuthenticatedUser:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token.")

    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        guild_ids = payload.get("guild_ids", [])
        if not any(gid in settings.discord_allowed_guild_ids for gid in guild_ids):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorised guild.")

        return AuthenticatedUser(
            id=payload.get("sub"),
            username=payload.get("username"),
            discriminator=payload.get("discriminator"),
            guild_ids=guild_ids,
            guild_roles=payload.get("guild_roles", {}),
            can_create_events=payload.get("can_create_events", False),
        )
    except JWTError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.") from exc


@router.get("/me", response_model=UserInfo)
async def get_me(user: AuthenticatedUser = Depends(get_current_user)) -> UserInfo:
    return UserInfo(
        id=user.id,
        username=user.username,
        discriminator=user.discriminator,
        guild_ids=user.guild_ids,
        guild_roles=user.guild_roles,
        can_create_events=user.can_create_events,
        alert_lead_minutes=settings.alert_lead_minutes,
    )
