# NANDA Adapter

Bring your local agent online: make it persistent, discoverable, and interoperable on the global Internet with NANDA.

* **Agent Bridge**: Routes `@agent_id` messages to local or registry‑discovered agents over HTTP/SSE, making your agent discoverable and easy to reach.
* **Multiple AI frameworks**: Use pure Python, LangChain, CrewAI, or your own logic.
* **Agent‑to‑Agent (A2A)**: Message passing across agents with optional message improvement.
* **MCP support**: Call Model Context Protocol tools over HTTP or SSE.
* **Registry integration**: Discover and register agents via a registry endpoint.
* **HTTP API**: Simple Flask API for health, sending messages, and rendering outputs.

---
## Architecture overview

* Provided by the external `nanda-adapter` package: agent bridge, message routing, registry integration, MCP routing, and the Flask HTTP API.
* In this folder: `examples/*` (runnable examples) and `nanda_utils/facts_provider.py` (helper for List39 Agent Facts).


#### Using @ Agent-to-Agent Communication:
Prefix your message with `@<agent_id>` to route it to a particular agent through the NANDA Agent Bridge.

**How it works**
1. The bridge extracts the first token beginning with `@` to determine the target `agent_id`.
2. If the `agent_id` is locally registered (e.g., via `AGENT_ID` or `NANDA(...).register(...)`), the message is delivered to that agent.

**Examples**
```text
@rephrase_agent Rephrase this sentence: I want to go to the park
```

##### Direct MCP Usage

* **Using a Remote MCP Registry**
  If you’re using a remote MCP Registry (e.g. *Smithery*), you can reference it in your NANDA request with the format:

  ```
  #<provider_registry>:<mcp_server_name> <message>
  ```

  The request is parsed in `agent_bridge.py`, which resolves the endpoint via the registry and routes the query to the appropriate remote agent.
  **Example:**

  ```
  #smithery:travel_mcp_agent find hotels in Lisbon
  ```

* **Custom Implementation Requesting Directly from a NANDA Agent**
  You can also have a NANDA agent send requests directly to your MCP using the format:

  ```
  <@nanda_mcp_agent> <tool> <message/values>
  ```

  This is parsed and executed as an MCP tool call over SSE/HTTP.
  **Example:**

  ```
  @mcp_agent add a=10 b=1
  ```
---

## Installation

**Prereqs**

* Python 3.8+

**Clone and install**

```bash
git clone https://github.com/redhat-et/cloud-native-agents.git
cd agent_discovery/nanda/adapter
python3 -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

---

## Examples in this repo

All examples live under `agent_discovery/nanda/adapter/examples/`.

* `rephrase_agent.py`: Minimal NANDA rewriter agent using local HTTP calls (Ollama required).
* `langchain_pirate_agent.py`: Pirate rewriter agent using LangChain with Ollama for inference.
* `mcp_agent.py`: NANDA agent that routes simple messages (ping/add/query) to MCP tools.
* `mcp_server.py`: Minimal MCP server with SSE transport used by `mcp_agent.py`.

---

### Agent Facts (List39) - Optional

Use the List39 Agent Facts Registry to create and retrieve agent's identity and capabilities.

- Reference: [List39 Agent Facts Registry](https://list39.org/)

**How this repo uses Agent Facts:**
- `nanda_utils/facts_provider.py` fetches JSON from `https://list39.org/@<agent>.json` and returns it as text.
- `examples/rephrase_agent.py` prepends those facts to the prompt when available.

**Configure which agent to use:**
- In code, `rephrase_agent.py` sets a single variable (e.g. `@rephrase_agent_fact`) and propagates it to the facts provider:

```python
# examples/rephrase_agent.py
os.environ["LIST39_AGENT"] = os.getenv("REPHRASE_AGENT_HANDLE", "@rephrase_agent_fact")
```

**Sanity checks:**
- Preview the raw facts via curl (replace the handle):

```bash
curl -s https://list39.org/@<agent_fact_name>.json
```
- Example Output:
```bash
{
  "id": "4fc989d7-1aec-4819-b706-c129d90b8e9f",
  "agent_name": "resphrase_agent_fact",
  "label": "mcp_agent_fact",
  "description": "This agent will rephrase the query with correct english that is clear and easily understandable.",
  "version": "1.0",
  "documentationUrl": "",
  "jurisdiction": "Ireland",
  "provider": {
    "name": "",
    "url": "",
    "did": "",
    "_id": "68c7f314aa6d6aff3d849d53"
  },
  "endpoints": {
    "adaptive_resolver": {
      "url": "",
      "policies": []
    },
    "static": [
      ""
    ],
    "_id": "68c7f314aa6d6aff3d849d54"
  },
  "capabilities": {
    "modalities": [
      "text"
    ],
    "streaming": false,
    "batch": false,
    "authentication": {
      "methods": [],
      "requiredScopes": [],
      "_id": "68c01f71aa6d6aff3d8490ac"
    },
    "_id": "68c01f71aa6d6aff3d8490ab"
  },
  "skills": [
    {
      "id": "chat",
      "description": "Basic chat functionality",
      "inputModes": [
        "text"
      ],
      "outputModes": [
        "text"
      ],
      "supportedLanguages": [
        "en"
      ],
      "_id": "68c01f71aa6d6aff3d8490ad"
    }
  ],
  "evaluations": {
    "performanceScore": 0,
    "availability90d": "",
    "lastAudited": "",
    "auditTrail": "",
    "auditorID": "",
    "_id": "68c01f71aa6d6aff3d8490ae"
  },
  "telemetry": {
    "enabled": false,
    "retention": "1d",
    "sampling": 0.1,
    "_id": "68c01f71aa6d6aff3d8490af"
  },
  "certification": {
    "level": "verified",
    "issuer": "NANDA",
    "issuanceDate": "2025-09-09T12:37:05.855Z",
    "expirationDate": "2026-09-09T12:37:05.855Z",
    "_id": "68c01f71aa6d6aff3d8490b0"
  },
  "created_at": "2025-09-09T12:37:05.858Z",
  "updated_at": "2025-09-15T11:05:56.619Z"
}                           
```


### 1) Minimal rephrase agent

**File:** `agent_discovery/nanda/adapter/examples/rephrase_agent.py`

Requires a running Ollama and the specified model.

**Prereqs**

```bash
# Install Ollama (macOS)
brew install ollama
ollama serve &
ollama pull llama3.2:3b-instruct-fp16
```


**Run**

Runs the NANDA Agent Bridge on port `6000` and the HTTP API on port `6001` (both HTTP).

```bash
cd agent_discovery/nanda/adapter
python examples/rephrase_agent.py
```

**Probe the API**

```bash
curl -s -X POST http://127.0.0.1:6001/api/send \
  -H 'Content-Type: application/json' \
  -d '{"message":"@rephrase_agent Rephrase this sentence: I want to go to the park"}' | jq
```

**Environment variables (optional)**

* `PORT` — bridge port (default `6000`)
* `API_PORT` — local API port (default `6001`)
* `AGENT_ID` — identifier for your agent (default `rephrase_agent`)

---

### 2.1) MCP: start the server

**File:** `agent_discovery/nanda/adapter/examples/mcp_server.py`

Starts a Starlette app that:

* Serves `/sse` for MCP over SSE
* Exposes tools: `ping`, `add`.

**Run the MCP server**

```bash
cd agent_discovery/nanda/adapter
python examples/mcp_server.py --port 6080
```

---

### 2.2) MCP: run the NANDA agent

**File:** `agent_discovery/nanda/adapter/examples/mcp_agent.py`

This agent routes simple messages like `ping <name>`, `add <a> <b>` (or named args), and `query <text>` to MCP tools over SSE.

**Run the agent in a new terminal**

```bash
cd agent_discovery/nanda/adapter
python examples/mcp_agent.py
```

**Test direct MCP calls**

```bash
# Ping MCP tool (two styles)
curl -s -X POST http://127.0.0.1:6007/api/send \
  -H 'Content-Type: application/json' \
  -d '{"message":"@mcp_agent ping Kevin"}' | jq

# Addition MCP tool
curl -s -X POST http://127.0.0.1:6007/api/send \
  -H 'Content-Type: application/json' \
  -d '{"message":"@mcp_agent add a=54 b=34"}' | jq
```

> Replace `6007` with the `API_PORT` value printed on startup if different.

**Config**

* `MCP_SERVER_URL` — default `http://127.0.0.1:6080/sse`
* `AGENT_ID` — default `mcp_agent`

---

### 3) LangChain + Ollama pirate rephrase agent

**File:** `agent_discovery/nanda/adapter/examples/langchain_pirate_agent.py`

Requires a running Ollama and the specified model.

**Prereqs**

```bash
# Install Ollama (macOS)
brew install ollama
ollama serve &
ollama pull llama3.2:3b-instruct-fp16
```

**Run**

```bash
cd agent_discovery/nanda/adapter
python examples/langchain_pirate_agent.py
```

**ENV**

* `OLLAMA_HOST` — default `http://127.0.0.1:11434`
* `OLLAMA_MODEL` — default `llama3.2:3b-instruct-fp16`

**Test**

Run the following to send a message to the LangChain agent:

```bash
curl -s -X POST http://127.0.0.1:6011/api/send \
  -H 'Content-Type: application/json' \
  -d '{"message":"@langchain_agent Please rewrite this more clearly: I want go park now"}' | jq
```
Cross-Agent Communication

To test communication from a LangChain agent to an HTTP-based agent, first ensure Example 1 is running. Then execute:

```bash
curl -s -X POST http://127.0.0.1:6011/api/send \
  -H 'Content-Type: application/json' \
  -d '{"message":"@rephrase_agent Please rewrite this more clearly: I want go park now"}' | jq
```

---

## HTTP API (exposed by `NANDA.start_server_api` from the `nanda-adapter` package)

When an example calls `NANDA(...).start_server_api(...)`, it exposes these endpoints:

* `GET /api/health` — basic status
* `POST /api/send` — send a message, returns `response` and `conversation_id`
* `GET /api/agents/list` — list registered agents via registry
* `POST /api/receive_message` — inbound hook used by the bridge to notify UI
* `GET /api/render` — fetches and clears the latest message file
* `GET /api/messages/stream` — Server‑Sent Events endpoint for UI streaming

Note: This adapter exposes an HTTP API only; it does not include a built‑in UI.

---

## Configuration

This folder uses a `.env` file loaded by the examples. Edit `.env` to change defaults.

**Key variables**:

* **Global**: `ANTHROPIC_API_KEY`, `SSL`
* **Ollama**: `OLLAMA_HOST`, `OLLAMA_MODEL`
* **Facts**: `REPHRASE_AGENT_HANDLE`, `LIST39_BASE`
* **Rephrase agent**: `REPHRASE_*` (domain, ids, ports, urls)
* **MCP server**: `MCP_SERVER_PORT`
* **MCP agent**: `MCP_AGENT_*` (id, ports, urls), `MCP_SERVER_URL`
* **LangChain agent**: `LANGCHAIN_AGENT_*` (id, ports, urls)

---

## Production notes (optional)

* To serve HTTPS, run `run_ui_agent_https.py` with `--ssl` and a valid `--cert/--key`, or run behind a reverse proxy (nginx, Caddy) that terminates TLS.
* If exposing to the Internet, set `PUBLIC_URL` and `API_URL`, and register the agent with your registry.

---

## Troubleshooting

* **API returns non‑text response**: ensure your message content is plain text; binary content is not supported.
* **MCP requests fail**: confirm the SSE URL, that the server is running, and that the agent has network access.
* **Ollama errors**: verify `ollama serve` is running and the model is pulled.
