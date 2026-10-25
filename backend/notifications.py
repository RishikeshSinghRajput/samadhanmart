import os
from typing import Any

import httpx

CHANNEL_WEBHOOKS = {
    "EMAIL": os.getenv("EMAIL_WEBHOOK_URL"),
    "WHATSAPP": os.getenv("WHATSAPP_WEBHOOK_URL"),
}


async def dispatch_otp(channel: str, recipient: str, otp: str, item_id: int) -> str:
    webhook_url = CHANNEL_WEBHOOKS[channel]
    if not webhook_url:
        return "MOCKED"

    payload: dict[str, Any] = {
        "channel": channel,
        "recipient": recipient,
        "message": f"Your SamadhanMart listing verification code is {otp}.",
        "item_id": item_id,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(webhook_url, json=payload)
        response.raise_for_status()
    return "SENT"
