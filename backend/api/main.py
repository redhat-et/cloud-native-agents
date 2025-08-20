import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import logging
from datetime import datetime

# Import predefined models and manager
from backend.core.agents import AgentManager, IssueRequest, IssueResponse
from backend.core.memory import conversation_memory
from backend.core.utils import ConsoleWithCapture

# Setup logging
logger = logging.getLogger(__name__)

# --- FastAPI App Initialization ---
app = FastAPI(
    title="GitHub Issue Agent Team API",
    description="An API to trigger an agent team to analyze a GitHub issue and suggest next steps.",
)

# --- CORS Middleware Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods including OPTIONS
    allow_headers=["*"],  # Allows all headers
)

@app.post("/github_webhook")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    if payload.get("action") == "opened" and "issue" in payload:
        issue_url = payload["issue"]["html_url"]
        # Use background task so webhook returns quickly
        async def background_task():
            manager = AgentManager()
            await manager.analyze_issue_with_comment(issue_url)
        background_tasks.add_task(background_task)
        return {"status": "accepted", "detail": f"Processing issue {issue_url}"}
    return {"status": "ignored", "reason": "Not an 'opened' issue event"}

# --- API Endpoints ---
@app.post("/issue_next_steps_with_comment", response_model=IssueResponse)
async def analyze_issue_with_comment(request: IssueRequest):
    """
    Accepts a GitHub issue URL, processes it with an agent team including commenter,
    and posts the suggested next steps as a comment to the GitHub issue.
    """
    print(f"Received request for issue with comment: {request.issue_link}")
    try:
        manager = AgentManager()
        result = await manager.analyze_issue_with_comment(request.issue_link)
        return result
    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/issue_next_steps_analysis", response_model=IssueResponse)
async def analyze_issue_without_comment(request: IssueRequest):
    """
    Accepts a GitHub issue URL, processes it with an agent team (excluding commenter),
    and returns the analysis and suggested next steps without posting to GitHub.
    """
    print(f"Received request for issue analysis only: {request.issue_link}")
    try:
        manager = AgentManager()
        result = await manager.analyze_issue_without_comment(request.issue_link)
        return result
    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for HITL
@app.websocket("/ws/issue_next_steps_with_hitl_comment")
async def analyze_issue_with_hitl_comment(websocket: WebSocket):
    """
    WebSocket endpoint for Human-in-the-Loop GitHub issue analysis.
    User input is only requested when the user_proxy agent is called during the conversation.
    """
    print("WebSocket route connected")
    await websocket.accept()
    websocket_closed = False

    async def _send_error_message(content: str):
        try:
            await websocket.send_json(AgentManager.convert_datetime_to_string({
                "type": "error",
                "content": content,
                "source": "system"
            }))
        except:
            pass

    async def _user_input(prompt: str, cancellation_token=None) -> str:
        nonlocal websocket_closed
        if websocket_closed:
            logger.error("WebSocket connection is closed, cannot get user input")
            return "TERMINATE"
        try:
            await websocket.send_json(AgentManager.convert_datetime_to_string({
                "type": "user_input_requested",
                "prompt": prompt,
                "source": "user_proxy"
            }))
            data = await asyncio.wait_for(websocket.receive_json(), timeout=300)
            # Accept both TextMessage and dict with 'content'
            if isinstance(data, dict) and "content" in data:
                return data["content"]
            elif hasattr(data, "content"):
                return data.content
            return "TERMINATE"
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for user input, defaulting to TERMINATE")
            websocket_closed = True
            await _send_error_message("Timeout waiting for user input. Connection closed.")
            return "TERMINATE"
        except Exception as e:
            logger.error(f"Error in _user_input: {str(e)}")
            websocket_closed = True
            await _send_error_message(f"Error getting user input: {str(e)}. Connection closed.")
            return "TERMINATE"

    try:
        data = await websocket.receive_json()
        if isinstance(data, dict) and "content" in data:
            issue_link = data["content"]
        else:
            await _send_error_message("Invalid message format. Expected 'content' field.")
            return
        logger.info(f"Received HITL request: {issue_link}")
        manager = AgentManager()
        stream = await manager.hitl_team_stream(issue_link, _user_input)    
        
        # Use ConsoleWithCapture to handle both console printing and WebSocket streaming
        _, final_output = await ConsoleWithCapture(stream, websocket=websocket)
        # Store human approved comment in memory if found
        session_id = f"hitl_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        await conversation_memory.store_conversation(
            user_query=issue_link,
            agent_response=final_output,
            session_id=session_id,
            metadata={"endpoint": "ws_issue_next_steps_with_hitl_comment", "agent": "user_proxy"}
        )
        logger.info(f"\n💾 [MEMORY STORE] User edited comment stored in memory: {final_output[:100]}...")
    
        logger.info("HITL Conversation stream completed")
        await websocket.close()
    except WebSocketDisconnect:
        logger.info("HITL WebSocket client disconnected")
        websocket_closed = True
    except Exception as e:
        logger.error(f"HITL WebSocket error: {str(e)}")
        websocket_closed = True
        await _send_error_message(f"Error: {str(e)}")

# --- Legacy endpoint for backward compatibility ---
@app.post("/issue_next_steps", response_model=IssueResponse)
async def analyze_issue(request: IssueRequest):
    """
    Legacy endpoint that redirects to the with-comment version for backward compatibility.
    """
    return await analyze_issue_with_comment(request)
