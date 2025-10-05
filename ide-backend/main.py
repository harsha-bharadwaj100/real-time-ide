import asyncio
import subprocess
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import os
from dotenv import load_dotenv
import google.generativeai as genai

# --- AI Integration Setup ---
load_dotenv()  # Load environment variables from .env file
# --- ADD THIS LINE FOR DEBUGGING ---
print(f"--- Loaded API Key: {os.getenv('GEMINI_API_KEY')} ---")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
# Use the newer, faster, and more reliable Flash model
model = genai.GenerativeModel("gemini-flash-latest")
# ---------------------------

app = FastAPI()

# Allow CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConnectionManager:
    """Manages active WebSocket connections for collaborative sessions."""

    def __init__(self):
        # Dictionary to store active connections for each session
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        """Accepts a new WebSocket connection and adds it to the session."""
        await websocket.accept()
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        self.active_connections[session_id].append(websocket)

    def disconnect(self, websocket: WebSocket, session_id: str):
        """Removes a WebSocket connection from the session."""
        self.active_connections[session_id].remove(websocket)

    async def broadcast(self, message: str, session_id: str, sender: WebSocket):
        """Broadcasts a message to all clients in a session except the sender."""
        for connection in self.active_connections.get(session_id, []):
            if connection is not sender:
                await connection.send_text(message)


manager = ConnectionManager()


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """Handles WebSocket connections for real-time collaboration."""
    await manager.connect(websocket, session_id)
    try:
        while True:
            # Wait for a message (code update) from a client
            data = await websocket.receive_text()
            # Broadcast the received code to all other clients in the session
            await manager.broadcast(data, session_id, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
        print(f"Client disconnected from session {session_id}")


@app.post("/execute")
async def execute_code(request: dict):
    """Executes Python code and returns the output."""
    code = request.get("code", "")
    try:
        # Execute the code in a separate process for basic sandboxing
        # The timeout prevents infinitely running code
        result = subprocess.run(
            ["python", "-c", code],
            capture_output=True,
            text=True,
            timeout=5,  # 5-second timeout
            check=True,
        )
        output = result.stdout
    except subprocess.CalledProcessError as e:
        # Capture errors from the executed code (e.g., syntax errors)
        output = e.stderr
    except subprocess.TimeoutExpired:
        output = "Execution timed out."
    except Exception as e:
        output = f"An unexpected error occurred: {str(e)}"

    return {"output": output}


# --- NEW AUTOCOMPLETE ENDPOINT ---
@app.post("/autocomplete")
async def autocomplete(request: dict):
    """Receives code and cursor position, returns an AI-generated completion."""
    code = request.get("code", "")

    if not code:
        return {"suggestion": ""}

    # Create a specific prompt for code completion
    prompt = f"""You are an expert Python programmer. Provide a single-line code completion for the following Python code. Do not repeat the code I have already written. Provide only the completion text.

# My Code:
{code}

# Your Completion:"""

    try:
        response = model.generate_content(prompt)
        # Clean up the response to get just the code
        suggestion = response.text.strip().replace("`", "").replace("python", "")
        return {"suggestion": suggestion}
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return {"suggestion": ""}
