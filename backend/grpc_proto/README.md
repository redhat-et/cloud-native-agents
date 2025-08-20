# Issue Analyzer gRPC Tool

This folder contains the gRPC server and client code for exposing the Issue Analyzer team as a callable tool for other agents and services.

## Overview
- The **gRPC server** wraps the Issue Analyzer team logic and exposes it via a gRPC API.
- The **gRPC client tool** allows any AutoGen agent (or other Python code) to call the Issue Analyzer team over gRPC as a function/tool.

## Folder Structure
- `grpc.proto` — gRPC service definition
- `pb2.py`, `pb2_grpc.py` — Generated Python code from the proto
- `server.py` — Async gRPC server exposing the Issue Analyzer team
- `client_and_tool.py` — Python FunctionTool for calling the gRPC server
- `test_tool.py` — Example: AutoGen agent using the gRPC tool
- `test_client.py` — Example: Direct gRPC client call

## How to Use

### 1. Start the gRPC Server
From the project root:
```sh
python -m backend.grpc.server
```
This will start the server on `localhost:50051` by default.

### 2. Use the Tool in AutoGen Agents
You can use the provided `analyze_issue_grpc_tool` in any AutoGen agent. Example:
```python
from backend.grpc.client_and_tool import analyze_issue_grpc_tool
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

model_client = OpenAIChatCompletionClient(model="gpt-4o")
agent = AssistantAgent(
    name="my_agent",
    model_client=model_client,
    tools=[analyze_issue_grpc_tool],
    system_message="You are a helpful assistant that can analyze GitHub issues using a gRPC tool."
)
```

### 3. Example Test
See `test_tool.py` for a working example of an agent calling the gRPC tool.
See `test_client.py` for a direct gRPC client call example.

### 4. Regenerating gRPC Code
If you change the proto file, regenerate the Python code:
```sh
python -m grpc_tools.protoc -I=backend/grpc --python_out=backend/grpc --grpc_python_out=backend/grpc backend/grpc/grpc.proto
```

## Requirements
- Python 3.8+
- `grpcio`, `grpcio-tools` (see `requirements.txt`)
- AutoGen, FastAPI, and other dependencies as per the project

## Notes
- All gRPC-related files are kept in this folder for modularity.
- Imports in Python files use relative imports for package compatibility.
- The gRPC tool can be used by any agent or service that can call Python async functions. 
