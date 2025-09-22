# MCP Registry Setup and Publishing Guide

This guide helps you set up and publish an MCP server using the `mcp-publisher` CLI and practice the full registry flow locally before publishing to the official registry.

### What you’ll accomplish
- Publish to a local registry (fast demo)
- Publish to the official registry (production)

### Who is this for?
- You’ve built (or are building) an MCP server and want to list it in a registry so clients can discover and install it.
- You prefer a safe, local dry-run before going public.

---

## Prerequisites

- **Docker** (for running a local registry)
- **Homebrew** (macOS/Linux) *or* Go to build from source
- **`mcp-publisher`** CLI

```bash
# Recommended install (macOS/Linux/WSL)
brew install mcp-publisher
```

---

## Key concepts
- **`server.json`**: The manifest for your MCP server consumed by the registry. It must follow the published schema (see example schema below).
- **Packages vs Remotes**:
  - **Packages:** clients install and run your server locally (e.g. from npm, using `stdio`). Best for offline/local use.  
  - **Remotes:** clients connect to a hosted server you run (`sse` or `streamable-http`). Best when your server needs an always-on endpoint. 
- **Registry API**: Primary routes are `GET /v0/servers` (list/search) and `GET /v0/servers/{id}` (details).

Why this matters: the registry uses your `server.json` to index, show details, and verify install sources; clients rely on this to find and connect to your server.

---

## Option A - Local Registry Setup

This path runs a **local MCP Registry** and publishes a demo server entry so you can show the flow **without owning a namespace**.

```bash
export REGISTRY="http://localhost:8080"
```
> Note: we will set `REGISTRY` once and reuse it.

### 1. Start a local registry

```bash
docker compose up -d
```

The API will be available at `http://localhost:8080/v0` with PostgreSQL and seed data. You can adjust environment variables in `docker-compose.yml` if needed.

---

### 2. Create and validate your `server.json`
If you don't already have a `server.json`, create one now:

```bash
# Generate a starter file in the current directory
mcp-publisher init
```

Or create it manually in the project root as `server.json` with at least these fields:

**Working Example** `server.json`:
```json
{
  "$schema": "https://static.modelcontextprotocol.io/schemas/2025-07-09/server.schema.json",
  "name": "io.github.<YOUR_GITHUB_USERNAME>/<your-server>",
  "description": "Short description of what your MCP server does",
  "status": "active",
  "version": "1.0.0",
  "repository": { "url": "https://github.com/<YOUR_GITHUB_USERNAME>/<your-repo>", "source": "github" },
  "remotes": [
    { "type": "streamable-http", "url": "https://<GITHUB_USERNAME>.github.io/mcp" }
  ]
}
```

- Use a namespace you control for `name` (for GitHub, `io.github.<YOUR_GITHUB_USERNAME>/<your-server>`).
- If you host a remote endpoint, set `remotes[].type` to `streamable-http` or `sse` and provide a reachable HTTPS URL.
- Increment `version` whenever you publish a new release.

Schema reference: https://registry.modelcontextprotocol.io/docs#/operations/publish-server (the `$schema` URL above is current as of this guide).

---

### 3. Authentication (local)

For this example, we’ll demonstrate authentication using **GitHub**.

Run the following command to login to your local registry:

```bash
mcp-publisher login github --registry="$REGISTRY"
```
> **Note:** Local registries often don’t require login, but this example shows the full flow.  

> For the **official registry**, authentication is always required (see Option B below).


---

### 4. Publish MCP Server

Run the command below to publish your `server.json` to the registry:

```bash
mcp-publisher publish --registry="$REGISTRY"
```
This will register your server entry in the registry so clients can discover it.

---

### 5. Search & capture the server ID

```bash
# Find your entry
curl -s "$REGISTRY/v0/servers?search=demo-mcp-server" | jq '.'

# (Optional) grab the latest ID into a shell variable
SERVER_ID=$(curl -s "$REGISTRY/v0/servers?search=demo-mcp-server&version=latest" \
  | jq -r '.servers[0]._meta["io.modelcontextprotocol.registry/official"].id')
echo "$SERVER_ID"
```

The Registry supports `search`, `version=latest`, pagination, etc. (See more queries below.)

---

### 6. Demo a new version & “latest” behavior

```bash
# bump version in server.json (example from 1.0.0 -> 1.0.1)
# (use your editor or the jq one-liner below under “Handy utilities”)
mcp-publisher publish --registry="$REGISTRY"

# show versions & which one is latest
curl -s "$REGISTRY/v0/servers?search=demo-mcp-server" \
  | jq '.servers[] | {version: .version, latest: ._meta["io.modelcontextprotocol.registry/official"].is_latest}'

# show only the latest version
curl -s "$REGISTRY/v0/servers?search=demo-mcp-server&version=latest" | jq '.'
```

*Note:* The `_meta["io.modelcontextprotocol.registry/official"]` block is part of the current preview metadata; naming may evolve.

---

### 7. Fetch full details by ID

```bash
SERVER_ID=${SERVER_ID:-$(curl -s "$REGISTRY/v0/servers?search=demo-mcp-server&version=latest" \
  | jq -r '.servers[0]._meta["io.modelcontextprotocol.registry/official"].id')}
curl -s "$REGISTRY/v0/servers/${SERVER_ID}" | jq '.'
```

`GET /v0/servers/{id}` returns a full entry with packages, remotes, etc.

---

### 8. Paginate (if you have lots of results)

```bash
# First page (limit 1)
curl -s "$REGISTRY/v0/servers?limit=1&search=demo-mcp-server" \
  | tee /tmp/page1.json | jq '.'

# Next page using next_cursor
NEXT=$(jq -r '.metadata.next_cursor' /tmp/page1.json)
[ "$NEXT" != "null" ] \
  && curl -s "$REGISTRY/v0/servers?limit=1&cursor=$NEXT&search=demo-mcp-server" | jq '.' \
  || echo "No next page"
```

---

### 9. Cleanup

```bash
# docker compose
docker compose down

# delete registry database
rm -rf .db  
```

---

## Option B - Publish to the official registry

### 1. Install the publisher (if not already):
```bash
brew install mcp-publisher
```

### 2. Authenticate (GitHub OAuth is the usual path):
```bash
# We will set REGISTRY once and reuse it.
export REGISTRY="https://registry.modelcontextprotocol.io"

# Authentication via GitHub
mcp-publisher login github --registry="$REGISTRY"
```
This opens a device-auth flow in your browser and stores a token locally.

### 3. Create and validate your `server.json` (skip Option A if you like)
If you don't already have a `server.json`, create one now:

```bash
# Generate a starter file in the current directory
mcp-publisher init
```

Or create it manually in the project root as `server.json` with at least these fields:

**Working Example** `server.json`:
```json
{
  "$schema": "https://static.modelcontextprotocol.io/schemas/2025-07-09/server.schema.json",
  "name": "io.github.<YOUR_GITHUB_USERNAME>/<your-server>",
  "description": "Short description of what your MCP server does",
  "status": "active",
  "version": "1.0.0",
  "repository": { "url": "https://github.com/<YOUR_GITHUB_USERNAME>/<your-repo>", "source": "github" },
  "remotes": [
    { "type": "streamable-http", "url": "https://<GITHUB_USERNAME>.github.io/mcp" }
  ]
}
```

- Use a namespace you control for `name` (for GitHub, `io.github.<YOUR_GITHUB_USERNAME>/<your-server>`).
- If you host a remote endpoint, set `remotes[].type` to `streamable-http` or `sse` and provide a reachable HTTPS URL.
- Increment `version` whenever you publish a new release.

Schema reference: https://registry.modelcontextprotocol.io/docs#/operations/publish-server (the `$schema` URL above is current as of this guide).


### 4. Publish:
```bash
mcp-publisher publish --registry="$REGISTRY"
```

### 5. Verify via API:
```bash
curl -s "$REGISTRY/v0/servers?search=io.github.<YOUR_GITHUB_USERNAME>/demo-mcp-server&version=latest" | jq '.'
```
Public API supports listing and fetching server details without auth.

---

## Handy utilities (copy-paste)

**Common queries:**
```bash
# search all servers with "github" in name/description
curl -s "$REGISTRY/v0/servers?search=github" | jq '.servers | length'

# latest only
curl -s "$REGISTRY/v0/servers?search=github&version=latest" | jq '.servers[0]'

# details by ID
curl -s "$REGISTRY/v0/servers/<UUID>" | jq '.'
```
API shapes may evolve during preview; see live docs for the latest params: https://registry.modelcontextprotocol.io/docs

---

## Appendix: Useful links

- **Registry repo** (publisher, local dev): https://github.com/modelcontextprotocol/registry
- **Live API reference**: https://registry.modelcontextprotocol.io/docs
- **Container image**: https://github.com/modelcontextprotocol/registry/pkgs/container/registry
- **Static schemas**: https://static.modelcontextprotocol.io/schemas/
