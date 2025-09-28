from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from html import escape
from typing import Dict, List, Tuple

from ...agents.interaction_agent.runtime import InteractionAgentRuntime, InteractionResult
from ...logging_config import logger


class InMemoryConversationLog:
    """In-memory conversation log for bridge sessions."""

    def __init__(self) -> None:
        self._entries: List[Tuple[str, str]] = []

    def record_user_message(self, content: str) -> None:
        self._append("user_message", content)

    def record_agent_message(self, content: str) -> None:
        self._append("agent_message", content)

    def record_reply(self, content: str) -> None:
        self._append("poke_reply", content)

    def record_wait(self, reason: str) -> None:  # pragma: no cover - not used but provided for parity
        self._append("wait", reason)

    def _append(self, tag: str, payload: str) -> None:
        self._entries.append((tag, str(payload)))

    def load_transcript(self) -> str:
        rendered: List[str] = []
        for tag, payload in self._entries:
            safe = escape(payload, quote=False)
            rendered.append(f"<{tag}>{safe}</{tag}>")
        return "\n".join(rendered)

    def clear(self) -> None:
        self._entries.clear()


class NullWorkingMemoryLog:
    """Stub working-memory log for bridge sessions."""

    def __init__(self) -> None:
        self._transcript: str = ""

    def append_entry(self, *_args, **_kwargs) -> None:  # pragma: no cover - no-op
        return

    def load_summary_state(self):  # pragma: no cover - summarization disabled for bridge
        from ..conversation.summarization.state import SummaryState

        return SummaryState.empty()

    def write_summary_state(self, _state) -> None:  # pragma: no cover - no-op
        return

    def render_transcript(self, *_args, **_kwargs) -> str:
        return self._transcript


@dataclass
class ConversationSession:
    """Encapsulates state for a single bridge conversation."""

    runtime: InteractionAgentRuntime
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class IMessageBridge:
    """Manage conversation sessions originating from iMessage."""

    def __init__(self) -> None:
        self._sessions: Dict[str, ConversationSession] = {}
        self._sessions_lock = asyncio.Lock()

    async def process_message(self, conversation_id: str, text: str) -> str:
        if not conversation_id:
            raise ValueError("Conversation ID required")
        session = await self._get_or_create_session(conversation_id)
        async with session.lock:
            result: InteractionResult = await session.runtime.execute(text)
        if not result.success:
            error = result.error or "LLM processing failed"
            logger.error(
                "iMessage bridge processing failed",
                extra={"conversation_id": conversation_id, "error": error},
            )
            raise RuntimeError(error)
        reply = (result.response or "").strip()
        if not reply:
            logger.warning(
                "iMessage bridge produced empty reply",
                extra={"conversation_id": conversation_id},
            )
        return reply

    async def _get_or_create_session(self, conversation_id: str) -> ConversationSession:
        try:
            return self._sessions[conversation_id]
        except KeyError:
            pass

        async with self._sessions_lock:
            if conversation_id in self._sessions:
                return self._sessions[conversation_id]

            conversation_log = InMemoryConversationLog()
            working_memory_log = NullWorkingMemoryLog()
            runtime = InteractionAgentRuntime(
                conversation_log=conversation_log,
                working_memory_log=working_memory_log,
            )
            session = ConversationSession(runtime=runtime)
            self._sessions[conversation_id] = session
            return session


_BRIDGE: IMessageBridge | None = None


def get_imessage_bridge() -> IMessageBridge:
    global _BRIDGE
    if _BRIDGE is None:
        _BRIDGE = IMessageBridge()
    return _BRIDGE


__all__ = ["get_imessage_bridge", "IMessageBridge"]
