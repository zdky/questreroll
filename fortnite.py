"""Epic Games / Fortnite API: auth, tokens refresh, quests and reroll.

This module knows nothing about telegram, it only talks to Epic Games
and stores tokens in the database.
"""

from datetime import datetime, timedelta

import aiohttp

from constants import FN_JSON, Headers, Links
from database import db
from utils import log, utc_now

# consider a token dead a bit earlier, to not use it right before expiration
TOKEN_EXPIRE_MARGIN = timedelta(minutes=2)


class EpicAPIError(Exception):
    pass


class EpicAPI:
    def __init__(self):
        self._session: aiohttp.ClientSession | None = None

    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def request(
        self,
        method: str,
        url: str,
        headers: dict,
        data: dict | None = None,
        json: dict | None = None,
    ) -> dict:
        """Request with json response, raises EpicAPIError on any failure."""
        try:
            async with self.session.request(
                method,
                url,
                headers=headers,
                data=data if method == "POST" else None,
                params=data if method == "GET" else None,
                json=json,
            ) as response:
                res_json = await response.json(content_type=None)
                status = response.status
        except (aiohttp.ClientError, TimeoutError, ValueError) as error:
            raise EpicAPIError(f"{method} {url}: {error!r}") from error

        if (
            status >= 400
            or not isinstance(res_json, dict)
            or "errorMessage" in res_json
        ):
            error_code = (
                res_json.get("errorCode") if isinstance(res_json, dict) else None
            )
            message = (
                res_json.get("errorMessage") if isinstance(res_json, dict) else res_json
            )
            raise EpicAPIError(
                f"{method} {url}: status={status}, {error_code}: {message}"
            )
        return res_json

    # Auth Step-1
    async def get_access_token(
        self, token: str, grant_type: str = "authorization_code"
    ) -> dict:
        """Epic Games Launcher token (access_token live 8h, refresh_token 23d)

        Args:
            token (str): auth_code or refresh_token
            grant_type (str): "authorization_code" or "refresh_token"
        """
        token_key = "refresh_token" if grant_type == "refresh_token" else "code"
        return await self.request(
            "POST",
            Links.oauth_api.format("token"),
            headers={
                "Authorization": Headers.access,
                "Content-Type": Headers.oauth_content_type,
            },
            data={"grant_type": grant_type, token_key: token},
        )

    # Auth Step-2
    async def get_exchange_code(self, access_token: str) -> str:
        """Exchange code (live 299 sec) for the Fortnite client auth."""
        res_json = await self.request(
            "GET",
            Links.oauth_api.format("exchange"),
            headers={"Authorization": f"bearer {access_token}"},
        )
        return res_json["code"]

    # Auth Step-3
    async def get_fortnite_token(
        self, token: str, grant_type: str = "exchange_code"
    ) -> dict:
        """Fortnite client token (access_token live 2h, refresh_token 8h)

        Args:
            token (str): exchange code or refresh token
            grant_type (str): "exchange_code" or "refresh_token"
        """
        token_key = (
            "exchange_code" if grant_type == "exchange_code" else "refresh_token"
        )
        return await self.request(
            "POST",
            Links.oauth_api.format("token"),
            headers={
                "Authorization": Headers.oauth,
                "Content-Type": Headers.oauth_content_type,
            },
            data={"grant_type": grant_type, token_key: token, "token_type": "eg1"},
        )

    async def login_by_launcher_token(self, acc_token: dict) -> dict:
        exchange_code = await self.get_exchange_code(acc_token["access_token"])
        return await self.get_fortnite_token(exchange_code)

    @staticmethod
    def profile_headers(access_token: str) -> dict:
        return {
            "User-Agent": Headers.user_agent,
            "Authorization": f"bearer {access_token}",
            "Content-Type": "application/json",
        }

    async def get_campaign(self, fn_token: dict) -> dict:
        """PvE (campaign) profile of the account."""
        res_json = await self.request(
            "POST",
            Links.profile_api.format(
                fn_token["account_id"], "ClientQuestLogin", "campaign"
            ),
            headers=self.profile_headers(fn_token["access_token"]),
            json={},
        )
        return res_json["profileChanges"][0]["profile"]

    async def reroll_quest(self, fn_token: dict, quest_id: str) -> None:
        await self.request(
            "POST",
            Links.profile_api.format(
                fn_token["account_id"], "FortRerollDailyQuest", "campaign"
            ),
            headers=self.profile_headers(fn_token["access_token"]),
            json={"questId": quest_id},
        )


api = EpicAPI()


def is_alive(token: dict, expires_key: str = "expires_at") -> bool:
    if not token or not token.get(expires_key):
        return False
    expires_at = datetime.fromisoformat(token[expires_key].replace("Z", "+00:00"))
    return expires_at - TOKEN_EXPIRE_MARGIN > utc_now()


async def login(user_id: int, auth_code: str) -> bool:
    """Login to Fortnite API with auth_code and save tokens."""
    try:
        acc_token = await api.get_access_token(auth_code)
        fn_token = await api.login_by_launcher_token(acc_token)
    except EpicAPIError as error:
        log.error(f"login(), user_id: {user_id}, {error}")
        return False
    await db.update(user_id, acc_token=acc_token, fn_token=fn_token)
    log.info(
        f"login(), user_id: {user_id}, logged in as {acc_token.get('displayName')}"
    )
    return True


async def get_valid_token(user_id: int) -> dict | None:
    """Alive fortnite token, refreshed if needed.

    Returns None (and removes saved tokens) if every token is dead.
    """
    user = db.get(user_id) or {}
    fn_token, acc_token = user.get("fn_token"), user.get("acc_token")

    if is_alive(fn_token):
        return fn_token

    # the refresh_token sometimes dies a few hours before its expires_at,
    # so on failure just go to the next step
    if is_alive(fn_token, "refresh_expires_at"):
        try:
            fn_token = await api.get_fortnite_token(
                fn_token["refresh_token"], "refresh_token"
            )
            await db.update(user_id, fn_token=fn_token)
            log.info(f"get_valid_token(), user_id: {user_id}, fn_token refreshed")
            return fn_token
        except EpicAPIError as error:
            log.warning(
                f"get_valid_token(), user_id: {user_id}, fn_token refresh: {error}"
            )

    if is_alive(acc_token, "refresh_expires_at"):
        try:
            acc_token = await api.get_access_token(
                acc_token["refresh_token"], "refresh_token"
            )
            fn_token = await api.login_by_launcher_token(acc_token)
            await db.update(user_id, acc_token=acc_token, fn_token=fn_token)
            log.info(f"get_valid_token(), user_id: {user_id}, all tokens refreshed")
            return fn_token
        except EpicAPIError as error:
            log.warning(
                f"get_valid_token(), user_id: {user_id}, acc_token refresh: {error}"
            )

    log.error(f"get_valid_token(), user_id: {user_id}, all tokens died")
    await db.update(user_id, acc_token={}, fn_token={})
    return None


def rerolls_left(campaign: dict) -> int:
    return (
        campaign.get("stats", {})
        .get("attributes", {})
        .get("quest_manager", {})
        .get("dailyQuestRerolls", 0)
    )


def parse_quests(campaign: dict, lang: str) -> dict:
    """Active daily quests with readable names and rewards.

    Args:
        campaign (dict): from EpicAPI.get_campaign()
        lang (str): user language

    Returns:
        {quest_id: {"quest_name", "progress", "reward", "difficulty"}}
    """
    items = FN_JSON["Items"]

    def translate(names: dict, default: str):
        return names.get(lang) or names.get("en") or default

    quests = {}
    for quest_id, item in campaign.get("items", {}).items():
        template_id = item.get("templateId", "")
        attributes = item.get("attributes", {})
        if not (
            template_id.lower().startswith("quest:daily_")
            and attributes.get("quest_state", "").lower() == "active"
        ):
            continue

        quest_json = items.get(template_id)
        if quest_json is None:
            log.warning(
                f"parse_quests(), unknown quest {template_id}, update fortnite.json"
            )
            quests[quest_id] = {
                "quest_name": template_id.split(":", 1)[-1],
                "progress": "?",
                "reward": "?",
                "difficulty": 0,
            }
            continue

        progress = []
        for obj_id, obj in quest_json.get("objectives", {}).items():
            done = attributes.get(f"completion_{obj_id}", 0)
            progress.append(f"{done}/{obj['count']} {translate(obj['name'], obj_id)}")

        rewards = []
        for reward_id, amount in quest_json.get("rewards", {}).items():
            reward_name = translate(items.get(reward_id, {}).get("name", {}), reward_id)
            if isinstance(reward_name, dict):  # ConditionalResource
                rewards.append(f"{amount}x {reward_name['PassedConditionItem']}")
                reward_name = reward_name["FailedConditionItem"]
            rewards.append(f"{amount}x {reward_name}")

        quests[quest_id] = {
            "quest_name": translate(quest_json["name"], template_id),
            "progress": ", ".join(progress),
            "reward": ", ".join(rewards),
            "difficulty": quest_json.get("difficulty", 0),
        }
    return quests
