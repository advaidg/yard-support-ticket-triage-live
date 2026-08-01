"""Auto-generated Chain Executor for Support Ticket Triage (live)."""
import asyncio
import json
import os

import httpx
from fastapi import FastAPI

app = FastAPI(title="Support Ticket Triage (live)")

TOKEN = ""
# h11 (httpx's transport) rejects "Bearer " with nothing after it as an
# illegal header value — only attach Authorization when a token exists.
AGENT_HEADERS = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}
AGENTS = [
    {"id": "classify", "agent_id": "fa08fb4c-86ab-4856-960f-f751b55e551f", "endpoint": "http://triage-classifier:9101", "timeout": 20},
    {"id": "sentiment", "agent_id": "b6f354f8-0746-4df8-a91e-da44df696f6d", "endpoint": "http://triage-sentiment:9102", "timeout": 20},
    {"id": "respond", "agent_id": "964a2673-82be-41e5-8f20-138c5d86345f", "endpoint": "http://triage-responder:9103", "timeout": 45},
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
    for agent in AGENTS:
        try:
            result = await call_agent(agent["endpoint"], current)
            trace.append({"agent": agent["id"], "status": "completed", "output": result})
            current = result.get("output", result)
        except Exception as e:
            trace.append({"agent": agent["id"], "status": "failed", "error": str(e)})
    return {"output": current, "trace": trace, "status": "completed"}


@app.get("/health")
async def health():
    return {"status": "ok", "engine": "chain_executor", "agents": len(AGENTS)}