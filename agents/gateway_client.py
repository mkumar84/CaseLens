"""HTTP client agents use to reach the gateway. This is the only channel any
agent has to case data — there is no direct database import anywhere in this
package, which is what makes the gateway's policy gates physically
unavoidable rather than an optional check an agent could skip."""

import httpx

from shared.config import settings

# Overridable only by tests, to route through an in-process ASGI transport
# instead of a real socket. Production code never sets this.
_transport_override: httpx.AsyncBaseTransport | None = None


def _set_transport_override(transport: httpx.AsyncBaseTransport | None) -> None:
    global _transport_override
    _transport_override = transport


async def gateway_post(path: str, *, json: dict | None = None, params: dict | None = None) -> dict:
    async with httpx.AsyncClient(
        base_url=settings.gateway_url, transport=_transport_override, timeout=60
    ) as client:
        response = await client.post(path, json=json, params=params)
        response.raise_for_status()
        return response.json()
