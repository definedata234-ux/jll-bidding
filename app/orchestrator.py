"""
Orchestrator — drives the tool-use loop for one opportunity's chat, against
whichever LLM provider app.config.LLM_PROVIDER selects.

Two providers are supported:
  - "anthropic" (default): Claude Messages API. system prompt is a separate
    top-level param; tool calls/results are content blocks within messages.
  - "deepseek": DeepSeek's OpenAI-compatible Chat Completions API. system
    prompt is a {"role": "system"} message; tool calls live on
    message.tool_calls, and results go back as {"role": "tool"} messages.

These two message-history shapes are NOT interchangeable — switching
LLM_PROVIDER mid-opportunity would break a stored conversation. That's an
accepted limitation for this prototype, not handled automatically.

Tool *implementations* (app/tools/*) are provider-agnostic either way —
only the request/response plumbing here differs.
"""
from __future__ import annotations

import json

from app import config
from app.config import MAX_TOKENS, MAX_TOOL_ITERATIONS, load_system_prompt
from app.logging_config import get_logger
from app.state import ConversationStore, OpportunityStore
from app.tools import OPENAI_TOOLS_SCHEMA, TOOLS_SCHEMA, dispatch

SYSTEM_PROMPT = load_system_prompt()
logger = get_logger(__name__)


class OrchestratorError(Exception):
    pass


def _system_prompt_for(opportunity_id: str) -> str:
    """The system prompt is static (loaded once from agent/system_prompt.md),
    but each conversation needs to know which opportunity_id it's actually
    operating on — otherwise the model has no way to know the ID and will
    invent one, causing every state-touching tool call to fail against a
    nonexistent record. This appends that session-specific fact without
    mutating the shared SYSTEM_PROMPT constant."""
    return (
        f"{SYSTEM_PROMPT}\n\n"
        "## ACTIVE OPPORTUNITY FOR THIS SESSION\n"
        f"opportunity_id: {opportunity_id}\n"
        "Always pass this exact value as opportunity_id in every tool call that "
        "requires one. Never invent, guess, or reuse an ID from a different "
        "conversation."
    )


class BidCopilotOrchestrator:
    def __init__(
        self,
        opportunity_store: OpportunityStore | None = None,
        conversation_store: ConversationStore | None = None,
        api_key: str | None = None,
        provider: str | None = None,
    ):
        self.opportunity_store = opportunity_store or OpportunityStore()
        self.conversation_store = conversation_store or ConversationStore()
        self.provider = (provider or config.LLM_PROVIDER).strip().lower()

        if self.provider == "deepseek":
            key = api_key or config.DEEPSEEK_API_KEY
            if not key:
                raise OrchestratorError(
                    "LLM_PROVIDER=deepseek but DEEPSEEK_API_KEY is not set. "
                    "Set it in your environment or .env file."
                )
            from openai import OpenAI  # local import: optional dependency unless used

            self.client = OpenAI(api_key=key, base_url=config.DEEPSEEK_BASE_URL)
            self.model = config.DEEPSEEK_MODEL
        elif self.provider == "anthropic":
            key = api_key or config.ANTHROPIC_API_KEY
            if not key:
                raise OrchestratorError(
                    "LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set. "
                    "Set it in your environment or .env file."
                )
            from anthropic import Anthropic  # local import: optional dependency unless used

            self.client = Anthropic(api_key=key)
            self.model = config.MODEL_NAME
        else:
            raise OrchestratorError(
                f"Unknown LLM_PROVIDER '{self.provider}'. Use 'anthropic' or 'deepseek'."
            )

    def chat(self, opportunity_id: str, user_message: str) -> str:
        # Confirm the opportunity exists up front, fail loudly otherwise.
        self.opportunity_store.get(opportunity_id)
        logger.info("chat_turn_start", opportunity_id=opportunity_id, provider=self.provider, model=self.model)
        if self.provider == "deepseek":
            reply = self._chat_deepseek(opportunity_id, user_message)
        else:
            reply = self._chat_anthropic(opportunity_id, user_message)
        logger.info("chat_turn_end", opportunity_id=opportunity_id, provider=self.provider, reply_chars=len(reply))
        return reply

    # ------------------------------------------------------------------
    # Anthropic (Claude) loop
    # ------------------------------------------------------------------
    def _chat_anthropic(self, opportunity_id: str, user_message: str) -> str:
        history = self.conversation_store.load(opportunity_id)
        history.append({"role": "user", "content": user_message})

        final_text = ""
        for _ in range(MAX_TOOL_ITERATIONS):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=MAX_TOKENS,
                system=_system_prompt_for(opportunity_id),
                tools=TOOLS_SCHEMA,
                messages=history,
            )

            assistant_content = [block.model_dump() for block in response.content]
            history.append({"role": "assistant", "content": assistant_content})

            if response.stop_reason != "tool_use":
                final_text = "".join(
                    block["text"] for block in assistant_content if block.get("type") == "text"
                )
                break

            tool_results = []
            for block in assistant_content:
                if block.get("type") != "tool_use":
                    continue
                tool_name = block["name"]
                tool_input = block["input"]
                tool_use_id = block["id"]
                try:
                    result = dispatch(tool_name, tool_input, self.opportunity_store)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": json.dumps(result, default=str),
                        }
                    )
                except Exception as exc:  # noqa: BLE001 - surfaced to the model, not swallowed
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": json.dumps({"error": str(exc)}),
                            "is_error": True,
                        }
                    )
            history.append({"role": "user", "content": tool_results})
        else:
            final_text = (
                "[Reached the maximum number of tool-call iterations for this turn. "
                "Please rephrase or break the request into smaller steps.]"
            )

        self.conversation_store.save(opportunity_id, history)
        return final_text

    # ------------------------------------------------------------------
    # DeepSeek (OpenAI-compatible) loop
    # ------------------------------------------------------------------
    def _chat_deepseek(self, opportunity_id: str, user_message: str) -> str:
        history = self.conversation_store.load(opportunity_id)
        if not history:
            history.append({"role": "system", "content": _system_prompt_for(opportunity_id)})
        history.append({"role": "user", "content": user_message})

        final_text = ""
        for _ in range(MAX_TOOL_ITERATIONS):
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=MAX_TOKENS,
                messages=history,
                tools=OPENAI_TOOLS_SCHEMA,
            )
            choice = response.choices[0]
            msg = choice.message

            assistant_entry: dict = {"role": "assistant", "content": msg.content or ""}
            if msg.tool_calls:
                assistant_entry["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls
                ]
            history.append(assistant_entry)

            if not msg.tool_calls:
                final_text = msg.content or ""
                break

            for tc in msg.tool_calls:
                tool_name = tc.function.name
                try:
                    tool_input = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    tool_input = {}
                try:
                    result = dispatch(tool_name, tool_input, self.opportunity_store)
                    content = json.dumps(result, default=str)
                except Exception as exc:  # noqa: BLE001 - surfaced to the model, not swallowed
                    content = json.dumps({"error": str(exc)})
                history.append({"role": "tool", "tool_call_id": tc.id, "content": content})
        else:
            final_text = (
                "[Reached the maximum number of tool-call iterations for this turn. "
                "Please rephrase or break the request into smaller steps.]"
            )

        self.conversation_store.save(opportunity_id, history)
        return final_text
