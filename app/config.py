"""
Central configuration and loaders for the JLL Bid Copilot prototype.

Loads the Stage 2 agent spec (system prompt + tool schemas) directly from
agent/system_prompt.md and agent/tools.json so there is a single source of
truth — this module never duplicates that content, only parses it.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional; env vars can be set directly.

# --- Paths -------------------------------------------------------------

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent
AGENT_DIR = PROJECT_ROOT / "agent"
DATA_DIR = APP_DIR / "data"
STORAGE_DIR = APP_DIR / "storage"
OPPORTUNITIES_DIR = STORAGE_DIR / "opportunities"
CONVERSATIONS_DIR = STORAGE_DIR / "conversations"

for _dir in (OPPORTUNITIES_DIR, CONVERSATIONS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

SYSTEM_PROMPT_PATH = AGENT_DIR / "system_prompt.md"
TOOLS_PATH = AGENT_DIR / "tools.json"

# --- Runtime settings ----------------------------------------------------

# Which LLM backs the orchestrator. "anthropic" (default, what Stage 2 was
# spec'd against) or "deepseek" (OpenAI-compatible API). Tool schemas and
# message-history shape differ between the two — see app/orchestrator.py.
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "anthropic").strip().lower()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
MODEL_NAME = os.environ.get("MODEL_NAME", "claude-sonnet-4-6")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "2048"))
MAX_TOOL_ITERATIONS = int(os.environ.get("MAX_TOOL_ITERATIONS", "8"))


def active_llm_key() -> str | None:
    """The API key for whichever provider LLM_PROVIDER currently selects."""
    return DEEPSEEK_API_KEY if LLM_PROVIDER == "deepseek" else ANTHROPIC_API_KEY


def active_llm_label() -> str:
    if LLM_PROVIDER == "deepseek":
        return f"deepseek:{DEEPSEEK_MODEL}"
    return f"anthropic:{MODEL_NAME}"

# Stage 1 default fit-score weights, confirmed for Stage 3 by the user.
DEFAULT_FIT_WEIGHTS = {
    "price": 0.40,
    "location": 0.25,
    "amenities": 0.20,
    "availability": 0.15,
}


def load_system_prompt() -> str:
    """Extract the verbatim system prompt block from agent/system_prompt.md."""
    text = SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    match = re.search(r"## SYSTEM PROMPT.*?```\n(.*?)```", text, re.S)
    if not match:
        raise ValueError(f"Could not locate fenced system prompt block in {SYSTEM_PROMPT_PATH}")
    return match.group(1).strip()


def load_tool_schemas() -> list[dict]:
    """Load the Claude tool-use schemas from agent/tools.json."""
    data = json.loads(TOOLS_PATH.read_text(encoding="utf-8"))
    return data["tools"]


def load_mock_data(filename: str):
    """Load a mock dataset JSON file from app/data/."""
    path = DATA_DIR / filename
    return json.loads(path.read_text(encoding="utf-8"))
