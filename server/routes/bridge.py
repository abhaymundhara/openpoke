from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from ..models import BridgeMessageRequest, BridgeMessageResponse
from ..services.bridge import get_imessage_bridge


router = APIRouter(prefix="/bridge", tags=["bridge"])


@router.post("/imessage", response_model=BridgeMessageResponse)
async def relay_imessage(payload: BridgeMessageRequest) -> BridgeMessageResponse:
    bridge = get_imessage_bridge()
    try:
        reply_text = await bridge.process_message(payload.conversation_id, payload.message)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return BridgeMessageResponse(reply=reply_text)


__all__ = ["router"]
