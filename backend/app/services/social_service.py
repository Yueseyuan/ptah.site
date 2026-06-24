"""Social media posting — Twitter/X, LinkedIn, Instagram (Meta Graph API)."""
import hashlib
import hmac
import logging
import time
from typing import Any
from urllib.parse import quote

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


# ── Twitter / X ─────────────────────────────────────────────────────────────

def _twitter_oauth1_header(method: str, url: str, params: dict[str, str]) -> str:
    """Build an OAuth 1.0a Authorization header for Twitter API v1.1/v2."""
    import base64
    import os

    nonce = base64.b64encode(os.urandom(16)).decode()
    ts = str(int(time.time()))

    oauth_params = {
        "oauth_consumer_key": settings.twitter_api_key,
        "oauth_nonce": nonce,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": ts,
        "oauth_token": settings.twitter_access_token,
        "oauth_version": "1.0",
    }
    all_params = {**params, **oauth_params}
    sorted_params = "&".join(
        f"{quote(k, safe='')}={quote(v, safe='')}"
        for k, v in sorted(all_params.items())
    )
    base_string = f"{method.upper()}&{quote(url, safe='')}&{quote(sorted_params, safe='')}"
    signing_key = (
        quote(settings.twitter_api_secret, safe="")
        + "&"
        + quote(settings.twitter_access_token_secret, safe="")
    )
    sig = base64.b64encode(
        hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
    ).decode()

    oauth_params["oauth_signature"] = sig
    header_parts = ", ".join(
        f'{quote(k, safe="")}="{quote(v, safe="")}"'
        for k, v in sorted(oauth_params.items())
    )
    return f"OAuth {header_parts}"


async def post_twitter(text: str, media_url: str | None = None) -> dict[str, Any]:
    """Post a tweet via Twitter API v2."""
    if not all([settings.twitter_api_key, settings.twitter_api_secret,
                settings.twitter_access_token, settings.twitter_access_token_secret]):
        return {"ok": False, "error": "Twitter API credentials not configured in .env"}

    url = "https://api.twitter.com/2/tweets"
    body: dict[str, Any] = {"text": text[:280]}

    auth_header = _twitter_oauth1_header("POST", url, {})
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            url,
            json=body,
            headers={
                "Authorization": auth_header,
                "Content-Type": "application/json",
            },
        )

    if resp.status_code in (200, 201):
        data = resp.json()
        tweet_id = data.get("data", {}).get("id", "")
        tweet_url = f"https://twitter.com/i/web/status/{tweet_id}"
        logger.info("Tweet posted: %s", tweet_url)
        return {"ok": True, "url": tweet_url, "id": tweet_id}

    logger.error("Twitter error %d: %s", resp.status_code, resp.text)
    return {"ok": False, "error": f"Twitter {resp.status_code}: {resp.text[:200]}"}


# ── LinkedIn ─────────────────────────────────────────────────────────────────

async def post_linkedin(text: str, media_url: str | None = None) -> dict[str, Any]:
    """Post a text update to LinkedIn via UGC Posts API."""
    if not settings.linkedin_access_token or not settings.linkedin_person_id:
        return {"ok": False, "error": "LINKEDIN_ACCESS_TOKEN and LINKEDIN_PERSON_ID not configured in .env"}

    author = f"urn:li:person:{settings.linkedin_person_id}"
    body: dict[str, Any] = {
        "author": author,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.linkedin.com/v2/ugcPosts",
            json=body,
            headers={
                "Authorization": f"Bearer {settings.linkedin_access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            },
        )

    if resp.status_code in (200, 201):
        post_id = resp.headers.get("x-restli-id", "")
        logger.info("LinkedIn post created: %s", post_id)
        return {"ok": True, "id": post_id}

    logger.error("LinkedIn error %d: %s", resp.status_code, resp.text)
    return {"ok": False, "error": f"LinkedIn {resp.status_code}: {resp.text[:200]}"}


# ── Instagram / Facebook (Meta Graph API) ────────────────────────────────────

async def post_instagram(text: str, image_url: str | None = None) -> dict[str, Any]:
    """Post to Instagram Business account via Meta Graph API (requires image_url for feed posts)."""
    if not settings.facebook_access_token or not settings.instagram_business_account_id:
        return {"ok": False, "error": "FACEBOOK_ACCESS_TOKEN and INSTAGRAM_BUSINESS_ACCOUNT_ID not configured in .env"}

    if not image_url:
        return {"ok": False, "error": "Instagram requires an image_url for feed posts"}

    account_id = settings.instagram_business_account_id
    token = settings.facebook_access_token
    base = "https://graph.facebook.com/v18.0"

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Step 1: create media container
        create_resp = await client.post(
            f"{base}/{account_id}/media",
            params={
                "image_url": image_url,
                "caption": text,
                "access_token": token,
            },
        )
        if create_resp.status_code != 200:
            return {"ok": False, "error": f"Instagram container error: {create_resp.text[:200]}"}

        container_id = create_resp.json().get("id")

        # Step 2: publish
        pub_resp = await client.post(
            f"{base}/{account_id}/media_publish",
            params={"creation_id": container_id, "access_token": token},
        )
        if pub_resp.status_code == 200:
            media_id = pub_resp.json().get("id", "")
            logger.info("Instagram post published: %s", media_id)
            return {"ok": True, "id": media_id}

        return {"ok": False, "error": f"Instagram publish error: {pub_resp.text[:200]}"}


async def post_facebook(text: str, image_url: str | None = None) -> dict[str, Any]:
    """Post to a Facebook Page via Graph API."""
    if not settings.facebook_access_token or not settings.facebook_page_id:
        return {"ok": False, "error": "FACEBOOK_ACCESS_TOKEN and FACEBOOK_PAGE_ID not configured in .env"}

    params: dict[str, str] = {
        "message": text,
        "access_token": settings.facebook_access_token,
    }
    if image_url:
        params["link"] = image_url

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"https://graph.facebook.com/v18.0/{settings.facebook_page_id}/feed",
            params=params,
        )

    if resp.status_code == 200:
        post_id = resp.json().get("id", "")
        logger.info("Facebook post created: %s", post_id)
        return {"ok": True, "id": post_id}

    return {"ok": False, "error": f"Facebook {resp.status_code}: {resp.text[:200]}"}


# ── Dispatcher ────────────────────────────────────────────────────────────────

async def post_social(
    platform: str,
    text: str,
    image_url: str | None = None,
) -> dict[str, Any]:
    """Route a post to the requested social platform."""
    p = platform.lower().strip()
    if p in ("twitter", "x"):
        return await post_twitter(text, image_url)
    if p == "linkedin":
        return await post_linkedin(text, image_url)
    if p in ("instagram", "ig"):
        return await post_instagram(text, image_url)
    if p in ("facebook", "fb"):
        return await post_facebook(text, image_url)
    return {"ok": False, "error": f"Unknown platform: {platform}. Use twitter, linkedin, instagram, or facebook."}
