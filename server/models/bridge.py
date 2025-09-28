from __future__ import annotations

from pydantic import BaseModel, Field


class BridgeMessageRequest(BaseModel):
    conversation_id: str = Field(..., min_length=1, max_length=256)
    message: str = Field(..., min_length=1)


class BridgeMessageResponse(BaseModel):
    reply: str = Field(default="")


__all__ = ["BridgeMessageRequest", "BridgeMessageResponse"]
