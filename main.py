"""Auto-generated Chain Executor for Support Ticket Triage (live)."""
import asyncio
import json
import os
import time

import httpx
from fastapi import FastAPI

app = FastAPI(title="Support Ticket Triage (live)")

TOKEN = ""
# h11 (httpx's transport) rejects "Bearer " with nothing after it as an
# illegal header value — only attach Authorization when a token exists.
AGENT_HEADERS = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
AGENTS = [
    {"id": "classify", "agent_id": "fa08fb4c-86ab-4856-960f-f751b55e551f", "name": "triage-classifier", "endpoint": "http://triage-classifier:9101", "timeout": 20},
    {"id": "sentiment", "agent_id": "b6f354f8-0746-4df8-a91e-da44df696f6d", "name": "triage-sentiment", "endpoint": "http://triage-sentiment:9102", "timeout": 20},
    {"id": "respond", "agent_id": "964a2673-82be-41e5-8f20-138c5d86345f", "name": "triage-responder", "endpoint": "http://triage-responder:9103", "timeout": 45},
]

# Endpoints baked in above come from the registry at generation time —
# correct when agents run wherever they're registered, stale when this
# orchestrator is deployed alongside its own freshly-spun-up agent pods
# elsewhere (a different cluster/VPC). YARD_AGENT_ENDPOINTS (JSON, node id
# -> endpoint), set by the K8s deploy generator, overrides per-node.
_ENDPOINT_OVERRIDES = json.loads(os.environ.get("YARD_AGENT_ENDPOINTS", "{}"))
for _agent in AGENTS:
    _agent["endpoint"] = _ENDPOINT_OVERRIDES.get(_agent["id"], _agent["endpoint"])

EDGES = [
    {"id": "", "source": "classify", "target": "sentiment", "transform": "passthrough"},
    {"id": "", "source": "sentiment", "target": "respond", "transform": "passthrough"},
]


async def call_agent(endpoint: str, input_data: dict) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.post(endpoint, json={"input": input_data}, headers=AGENT_HEADERS, timeout=240)
        resp.raise_for_status()
        return resp.json()


@app.post("/invoke")
async def invoke(input: dict):
    current = input.get("input", input)
    trace = []
    for i, agent in enumerate(AGENTS):
        start = time.monotonic()
        try:
            result = await call_agent(agent["endpoint"], current)
            duration_ms = int((time.monotonic() - start) * 1000)
            # Mission Control's trace step renderer keys rows by `step` and
            # reads `agent_name`/`duration_ms` (matches the local
            # chain_executor's own trace shape) — this used to emit `agent`
            # with no `step` or timing at all, so every deployed-
            # orchestrator invoke rendered blank step names, "(ms)" with no
            # number, and React key warnings for the undefined `step`.
            trace.append({"step": i + 1, "agent_name": agent["name"], "status": "completed", "output": result, "duration_ms": duration_ms})
            current = result.get("output", result)
        except Exception as e:
            duration_ms = int((time.monotonic() - start) * 1000)
            trace.append({"step": i + 1, "agent_name": agent["name"], "status": "failed", "error": str(e), "duration_ms": duration_ms})
    return {"output": current, "trace": trace, "status": "completed"}


@app.get("/health")
async def health():
    return {"status": "ok", "engine": "chain_executor", "agents": len(AGENTS)}