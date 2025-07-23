# cloud-native-agents

Platform for creating and deploying single and multi-agent AI systems on Kubernetes and OpenShift.

---

## What is this project?

**cloud-native-agents** is a platform for building, running, and deploying AI agent teams. An example team for the Github environment can analyze issues and PRs, suggest next steps, and automate workflows. It consists of:
- **Backend**: FastAPI service orchestrating agent teams using LLMs and external tools.
- **Frontend**: React UI for interacting with the agent platform.
- **OpenShift Manifests**: Kubernetes YAMLs for easy deployment on OpenShift.

---

## Running Locally

### Prerequisites
- Python 3.12+
- Node.js 18+
- [Podman](https://podman.io/) or Docker (for container builds)

### 1. Backend (API)

#### a. Install dependencies
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### b. Set environment variables
See [GitHub MCP Server Setup](https://github.com/github/github-mcp-server) for instructions on deploying your own MCP server.

Create a `.env` file in `backend/` with:
```
OPENAI_API_KEY=your-openai-key
TAVILY_API_KEY=your-tavily-key
GITHUB_MCP_URL=https://your-mcp-server
```

#### c. Run the backend
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8080
```

### 2. Frontend (UI)

#### a. Install dependencies
```bash
cd UI
npm install
```

#### b. Run the frontend
```bash
npm run dev
```

- The frontend will be available at [http://localhost:5173](http://localhost:5173) (default Vite port).
- By default, it expects the backend at `http://localhost:8080`.
- To change the backend API URL, set the environment variable `REACT_APP_API_BASE_URL` in a `.env` file or use the runtime `API_BASE_URL` variable when running the container. (To be fixed, currently update the config.ts file.)

---

## Building & Running with Containers

### Backend
```bash
cd backend
podman build -t cloud-native-agents-backend .
podman run --env-file .env -p 8080:8080 cloud-native-agents-backend
```

### Frontend
```bash
cd UI
podman build -t cloud-native-agents-frontend .
podman run -e API_BASE_URL=http://localhost:8080 -p 8080:8080 cloud-native-agents-frontend
```

---

## Deploying on OpenShift

### 1. Prepare Secrets
Edit `openshift/backend/secrets.yaml` and fill in your API keys:
```yaml
stringData:
  OPENAI_API_KEY: <your-openai-key>
  TAVILY_API_KEY: <your-tavily-key>
  GITHUB_MCP_URL: <your-mcp-server-url>
```
Apply the secret:
```bash
oc apply -f openshift/backend/secrets.yaml
```

### 2. Deploy Backend
```bash
oc apply -f openshift/backend/deployment.yaml
oc apply -f openshift/backend/service.yaml
oc apply -f openshift/backend/route.yaml
```

### 3. Deploy Frontend
```bash
oc apply -f openshift/frontend/deployment.yaml
oc apply -f openshift/frontend/service.yaml
oc apply -f openshift/frontend/route.yaml
```

### 4. Access the Application
- The OpenShift routes will expose public URLs for both frontend and backend.
- The frontend expects the backend API at the route defined in `API_BASE_URL` (see `openshift/frontend/deployment.yaml`).

---

## Environment Variables

### Backend
- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `TAVILY_API_KEY`: Your Tavily API key (required)
- `GITHUB_MCP_URL`: URL for the MCP server (required).

### Frontend
- `API_BASE_URL`: The base URL for the backend API (default: `http://localhost:8080`)
- Can be set at runtime for the container or via `.env` for local dev

---

## Project Structure
- `backend/` — FastAPI backend service
- `UI/` — React frontend
- `openshift/` — OpenShift deployment manifests

---

## License
See [LICENSE](LICENSE).

## Recognition

This project was developed with the assistance of AI tools for code and text generation, including:
- [ChatGPT](https://chat.openai.com/) by OpenAI
- [Gemini](https://gemini.google.com/) by Google
- [Cursor](https://https://www.cursor.com/) AI-powered code editor
