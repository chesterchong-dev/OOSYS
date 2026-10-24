"""Small synchronous wrapper around the public HTTPX ASGI transport."""
import asyncio

import httpx
from fastapi import FastAPI


def asgi_get(
    app: FastAPI,
    path: str,
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    """Send an in-process GET request without opening a network socket."""
    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://oosys.test"
        ) as client:
            return await client.get(path, headers=headers)

    return asyncio.run(send_request())
