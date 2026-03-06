from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

import httpx
from pydantic import BaseModel

from config import config


class NeuroUsersApiError(RuntimeError):
    """Raised when neurousers API returns an unexpected response."""


class CreateUserRequest(BaseModel):
    """Payload for POST /admin/create-user (idempotent upsert by user id)."""

    id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    photo_url: str | None = None
    role: int | None = None
    license_end_date: datetime | None = None
    balance: int | None = None
    ref_code: str | None = None
    or_api_key: str | None = None
    or_api_hash: str | None = None
    or_model: str | None = None


class CreateUserResponse(BaseModel):
    """Response from POST /admin/create-user."""

    status: Literal["created", "updated"]
    user_id: int


class OpenRouterSettingsRequest(BaseModel):
    api_key: str | None = None
    api_hash: str | None = None
    model: str | None = None


class OpenRouterSettingsResponse(BaseModel):
    api_key: str | None
    api_hash: str | None
    model: str | None


class UserBalanceResponse(BaseModel):
    balance_kopecks: int
    balance_rub: float


class AdminLicenseRequest(BaseModel):
    username: str
    days: int


class AdminBalanceRequest(BaseModel):
    username: str
    amount: int


class AdminActionResponse(BaseModel):
    status: Literal["success", "error"]
    message: str


class UserMeResponse(BaseModel):
    id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    photo_url: str | None
    role: str
    balance: int
    has_license: bool
    ref_code: str | None
    impersonated: bool | None = None
    real_user_id: int | None = None


class InternalUserStateRequest(BaseModel):
    user_id: int


class InternalUserStateResponse(BaseModel):
    user_id: int
    balance_kopecks: int
    api_key: str | None
    api_hash: str | None
    model: str | None


class InternalSetOpenRouterRequest(BaseModel):
    user_id: int
    api_key: str | None = None
    api_hash: str | None = None
    model: str | None = None


class InternalUsernamesRequest(BaseModel):
    user_ids: list[int]


class InternalUsernameResponse(BaseModel):
    user_id: int
    username: str | None


class InternalUsernamesResponse(BaseModel):
    items: list[InternalUsernameResponse]


class InternalDebitBalanceRequest(BaseModel):
    user_id: int
    amount_kopecks: int


class InternalDebitBalanceResponse(BaseModel):
    status: Literal["ok", "insufficient_funds", "not_found"]
    balance_kopecks: int | None


class NeuroUsersClient:
    """
    Async typed client for neurousers internal API.

    Auth:
    - Sends `X-Internal-Token` header for all requests.

    Methods:
    - `create_or_update_user`: idempotent upsert of user profile in neurousers.
    - `get_openrouter_settings`: read user OpenRouter settings by access token.
    - `set_openrouter_settings`: update user OpenRouter settings by access token.
    - `get_balance`: read user balance by access token.
    - `get_me`: read current user data by access token.
    - `admin_extend_license`: admin-only license extension (bearer token).
    - `admin_add_balance`: admin-only balance top-up (bearer token).
    - `internal_get_user_state`: read balance/openrouter settings by user id.
    - `internal_set_openrouter_settings`: update openrouter settings by user id.
    - `internal_get_usernames`: read usernames by user ids.
    - `internal_debit_balance`: atomically debit user balance (kopecks).
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        internal_token: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self._base_url = base_url or str(config.neurousers.url)
        self._internal_token = internal_token or config.neurousers.internal_token.get_secret_value()
        self._timeout = timeout_seconds or config.neurousers.timeout_seconds
        self._client: httpx.AsyncClient | None = None

    def _internal_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Internal-Token": self._internal_token,
        }

    @staticmethod
    def _bearer_headers(access_token: str) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "NeuroUsersClient":
        await self._get_client()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self._base_url.rstrip('/')}{path}"
        try:
            client = await self._get_client()
            response = await client.request(method, url, headers=headers, json=json)
        except httpx.HTTPError as exc:
            raise NeuroUsersApiError(f"Request failed: {method} {url}: {exc}") from exc

        if response.status_code >= 400:
            raise NeuroUsersApiError(
                f"Request failed: {method} {url} -> {response.status_code}: {response.text}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise NeuroUsersApiError(f"Invalid JSON response from {url}: {response.text}") from exc

    async def create_or_update_user(self, payload: CreateUserRequest) -> CreateUserResponse:
        """
        Create or update user in neurousers by id.

        Endpoint:
        - `POST /admin/create-user`

        Returns:
        - `status='created'` when user is inserted.
        - `status='updated'` when existing user is updated.
        """

        data = await self._request(
            "POST",
            "/admin/create-user",
            headers=self._internal_headers(),
            json=payload.model_dump(mode="json", exclude_none=True),
        )
        return CreateUserResponse.model_validate(data)

    async def get_openrouter_settings(self, access_token: str) -> OpenRouterSettingsResponse:
        data = await self._request(
            "GET",
            "/auth/openrouter-settings",
            headers=self._bearer_headers(access_token),
        )
        return OpenRouterSettingsResponse.model_validate(data)

    async def set_openrouter_settings(
        self,
        access_token: str,
        payload: OpenRouterSettingsRequest,
    ) -> OpenRouterSettingsResponse:
        data = await self._request(
            "POST",
            "/auth/openrouter-settings",
            headers=self._bearer_headers(access_token),
            json=payload.model_dump(exclude_none=True),
        )
        return OpenRouterSettingsResponse.model_validate(data)

    async def get_balance(self, access_token: str) -> UserBalanceResponse:
        data = await self._request(
            "GET",
            "/auth/balance",
            headers=self._bearer_headers(access_token),
        )
        return UserBalanceResponse.model_validate(data)

    async def get_me(self, access_token: str) -> UserMeResponse:
        data = await self._request(
            "GET",
            "/auth/me",
            headers=self._bearer_headers(access_token),
        )
        return UserMeResponse.model_validate(data)

    async def admin_extend_license(
        self,
        access_token: str,
        payload: AdminLicenseRequest,
    ) -> AdminActionResponse:
        data = await self._request(
            "POST",
            "/admin/license",
            headers=self._bearer_headers(access_token),
            json=payload.model_dump(),
        )
        return AdminActionResponse.model_validate(data)

    async def admin_add_balance(
        self,
        access_token: str,
        payload: AdminBalanceRequest,
    ) -> AdminActionResponse:
        data = await self._request(
            "POST",
            "/admin/balance",
            headers=self._bearer_headers(access_token),
            json=payload.model_dump(),
        )
        return AdminActionResponse.model_validate(data)

    async def internal_get_user_state(
        self,
        payload: InternalUserStateRequest,
    ) -> InternalUserStateResponse:
        data = await self._request(
            "POST",
            "/admin/internal/user-state",
            headers=self._internal_headers(),
            json=payload.model_dump(),
        )
        return InternalUserStateResponse.model_validate(data)

    async def internal_set_openrouter_settings(
        self,
        payload: InternalSetOpenRouterRequest,
    ) -> InternalUserStateResponse:
        data = await self._request(
            "POST",
            "/admin/internal/set-openrouter-settings",
            headers=self._internal_headers(),
            json=payload.model_dump(exclude_none=True),
        )
        return InternalUserStateResponse.model_validate(data)

    async def internal_get_usernames(
        self,
        payload: InternalUsernamesRequest,
    ) -> InternalUsernamesResponse:
        data = await self._request(
            "POST",
            "/admin/internal/usernames",
            headers=self._internal_headers(),
            json=payload.model_dump(),
        )
        return InternalUsernamesResponse.model_validate(data)

    async def internal_debit_balance(
        self,
        payload: InternalDebitBalanceRequest,
    ) -> InternalDebitBalanceResponse:
        data = await self._request(
            "POST",
            "/admin/internal/debit-balance",
            headers=self._internal_headers(),
            json=payload.model_dump(),
        )
        return InternalDebitBalanceResponse.model_validate(data)
