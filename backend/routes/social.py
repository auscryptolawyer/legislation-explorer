"""Social Post Composer — FastAPI backend.

Endpoints consumed by the social-composer.html frontend.
Covers the three external integrations:
  - OpenRouter (draft generation)
  - litterbox (image hosting, 72h expiry)
  - Buffer via mcporter (draft creation, never publish)

No secrets reach the browser. No subagent delegation.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

logger = logging.getLogger(__name__)
router = APIRouter(tags=["social"])

# ── Config ────────────────────────────────────────────────────────────
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = "openai/gpt-5.6-luna"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

MCPORTER_CONFIG = Path.home() / ".config" / "mcporter" / "config.json"

# Voice rules — loaded from the buffer-social-post skill at build time.
# Embedded here as a fallback so the endpoint is self-contained.
VOICE_RULES = """# Harrison voice
- Simplifies the complex. States the point plainly.
- Dry, self-deprecating, lightly humorous.
- No enthusiasm performance. No thought-leader posture.
- Trusts the reader to keep up. No over-explaining.

# Blacksheep voice
- Dry, technical, numbers-forward.
- Confident, clear, a little rebellious.
- Proof over promise. No fluff.

# Platform rules
- LinkedIn: 2-5 short paragraphs, Unicode bold for headlines, URL in plain text, real line breaks.
- X/Twitter: ≤ 280 chars, condensed to core message, plain URL.

# Anti-slop checklist (must run on output)
- NO em dashes. Use commas, periods, or parentheses.
- NO negative parallelism ("It's not X, it's Y").
- NO short punchy fragments as paragraphs.
- NO anaphora (3+ sentences starting with the same word).
- NO "what matters is", "the difference is", "the real question is".
- NO "quietly", "delve", "tapestry", "landscape", "leverage", "seamlessly".
- NO "here's the thing", "imagine a world where", "think of it as".
- NO short staccato declarative sentences in a row.
- NO markdown ** on LinkedIn. Use Unicode bold if needed.
- One-word sentences are not allowed. Merge them.
- URL must be in plain text, not Unicode bold.
- Use proper line breaks (newlines, not escaped \\n)."""


# ── Models ────────────────────────────────────────────────────────────
class GenerateRequest(BaseModel):
    topic: str
    account: str  # "harrison" | "blacksheep"
    platform: str  # "linkedin" | "x"

    @field_validator("account")
    @classmethod
    def valid_account(cls, v: str) -> str:
        if v not in ("harrison", "blacksheep"):
            raise ValueError("account must be 'harrison' or 'blacksheep'")
        return v

    @field_validator("platform")
    @classmethod
    def valid_platform(cls, v: str) -> str:
        if v not in ("linkedin", "x"):
            raise ValueError("platform must be 'linkedin' or 'x'")
        return v


class CondenseRequest(BaseModel):
    text: str
    account: str  # "harrison" | "blacksheep"

    @field_validator("account")
    @classmethod
    def valid_account(cls, v: str) -> str:
        if v not in ("harrison", "blacksheep"):
            raise ValueError("account must be 'harrison' or 'blacksheep'")
        return v


class PushRequest(BaseModel):
    text: str
    channel_id: str
    image_data_url: str | None = None
    saveToDraft: bool = True

    @field_validator("saveToDraft")
    @classmethod
    def drafts_only(cls, v: bool) -> bool:
        if not v:
            raise ValueError("saveToDraft must be true — no publish path exists")
        return v


# ── Helpers ────────────────────────────────────────────────────────────

def _build_prompt(topic: str, account: str, platform: str) -> str:
    """Build the system + user prompt for OpenRouter."""
    voice = "harrison" if account == "harrison" else "blacksheep"
    plat = "LinkedIn" if platform == "linkedin" else "X/Twitter"
    return f"""{VOICE_RULES}

Write a {plat} post for the {voice} account about the following topic.
Return ONLY the post text, no preamble, no commentary, no markdown fences.

Topic: {topic}"""


def _call_openrouter(prompt: str, max_tokens: int = 600) -> str:
    """Call the OpenRouter API and return the generated text."""
    if not OPENROUTER_API_KEY:
        raise HTTPException(503, "OpenRouter API key not configured")

    resp = requests.post(
        OPENROUTER_URL,
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": OPENROUTER_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.7,
        },
        timeout=60,
    )
    if resp.status_code != 200:
        logger.error("OpenRouter %s: %s", resp.status_code, resp.text[:500])
        raise HTTPException(502, f"OpenRouter error: {resp.status_code}")

    data = resp.json()
    text = data["choices"][0]["message"]["content"].strip()

    # Belt-and-braces: strip em dashes the model may have emitted
    text = text.replace("—", ", ").replace("–", "-")
    # Strip markdown bold markers
    text = text.replace("**", "")
    # Strip markdown code fences if present
    text = re.sub(r"^```.*?\n|```$", "", text, flags=re.MULTILINE).strip()

    return text


def _upload_to_litterbox(image_data_url: str) -> str:
    """Upload a base64 PNG to litterbox (72h expiry). Returns the URL."""
    try:
        raw = base64.b64decode(image_data_url.split(",", 1)[1])
    except (IndexError, ValueError) as e:
        raise HTTPException(400, f"Invalid image data URL: {e}")

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(raw)
        tmp_path = f.name

    try:
        with open(tmp_path, "rb") as f:
            resp = requests.post(
                "https://litterbox.catbox.moe/resources/internals/api.php",
                data={"reqtype": "fileupload", "time": "72h"},
                files={"fileToUpload": ("card.png", f, "image/png")},
                timeout=30,
            )
        os.unlink(tmp_path)
        if resp.status_code != 200:
            raise HTTPException(502, f"litterbox error: {resp.status_code}")
        url = resp.text.strip()
        if not url.startswith("https://"):
            raise HTTPException(502, f"litterbox returned unexpected response: {url}")
        return url
    except requests.RequestException as e:
        os.unlink(tmp_path)
        raise HTTPException(502, f"litterbox upload failed: {e}")


def _call_buffer_create_post(text: str, channel_id: str, media_url: str | None = None) -> str:
    """Call Buffer's create_post via mcporter. Returns the post ID."""
    if not MCPORTER_CONFIG.exists():
        raise HTTPException(503, "mcporter config not found")

    with open(MCPORTER_CONFIG) as f:
        cfg = json.load(f)

    token = (
        cfg.get("mcpServers", {})
        .get("buffer", {})
        .get("env", {})
        .get("BUFFER_API_TOKEN")
    )
    if not token:
        raise HTTPException(503, "BUFFER_API_TOKEN not found in mcporter config")

    assets = []
    if media_url:
        assets.append({"image": {"url": media_url}})

    # Build the mcporter call
    env = {**os.environ, "BUFFER_API_TOKEN": token}
    args = [
        "npx", "mcporter", "call", "buffer.create_post",
        f"channelId={channel_id}",
        "schedulingType=automatic",
        "mode=addToQueue",
        f"text={text}",
        "saveToDraft=true",
    ]
    if assets:
        args.append(f"assets={json.dumps(assets)}")

    try:
        result = subprocess.run(args, capture_output=True, text=True, env=env, timeout=30)
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Buffer API timed out")
    except FileNotFoundError:
        raise HTTPException(503, "mcporter (npx) not found")

    if result.returncode != 0:
        logger.error("Buffer mcporter error: %s", result.stderr[:500])
        raise HTTPException(502, f"Buffer API error: {result.stderr[:200]}")

    # Try to extract post ID from the JSON response
    try:
        resp_data = json.loads(result.stdout)
        # Check for MCP-level errors in the response
        if isinstance(resp_data, dict) and resp_data.get("error"):
            err_msg = str(resp_data["error"])[:200]
            logger.error("Buffer API error in response: %s", err_msg)
            raise HTTPException(502, f"Buffer API error: {err_msg}")
        if isinstance(resp_data, dict):
            post_id = resp_data.get("id", resp_data.get("_id", "unknown"))
        else:
            post_id = str(resp_data)
        if post_id.startswith("MCP error") or "error" in str(post_id).lower():
            raise HTTPException(502, f"Buffer API error: {post_id}")
        return post_id
    except (json.JSONDecodeError, TypeError):
        # Fallback: return the raw response
        return result.stdout.strip()[:100]


# ── Endpoints ──────────────────────────────────────────────────────────

@router.post("/api/social/generate")
def generate(req: GenerateRequest):
    """Generate a draft post for one account and platform."""
    prompt = _build_prompt(req.topic, req.account, req.platform)
    text = _call_openrouter(prompt)
    return {"draft": text}


@router.post("/api/social/condense")
def condense(req: CondenseRequest):
    """Condense a LinkedIn draft to an X/Twitter draft (≤280 chars)."""
    prompt = f"""{VOICE_RULES}

Condense the following LinkedIn post to an X/Twitter post.
- Must be ≤ 280 characters.
- Keep the core message. Strip setup, context, and CTA.
- Keep Unicode formatting if present.
- URL in plain text.
- Return ONLY the post text, no preamble.

LinkedIn post:
{req.text}"""

    text = _call_openrouter(prompt, max_tokens=200)

    # Enforce char limit
    if len(text) > 280:
        text = text[:277] + "..."

    return {"draft": text}


@router.post("/api/social/push")
def push(req: PushRequest):
    """Create a Buffer draft on one channel, optionally with an image."""
    media_url = None
    if req.image_data_url:
        media_url = _upload_to_litterbox(req.image_data_url)
        logger.info("Uploaded card image to %s", media_url)

    post_id = _call_buffer_create_post(req.text, req.channel_id, media_url)
    logger.info("Buffer draft created: %s (channel %s)", post_id, req.channel_id)

    return {"status": "drafted", "post_id": post_id}