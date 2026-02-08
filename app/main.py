from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
import asyncio
import json
import uuid
import os
import re
import logging
import subprocess
import shlex

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("opencode")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Workspace setup
WORKSPACE_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "../workspace"))
os.makedirs(WORKSPACE_BASE, exist_ok=True)

# Mount static files
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../static"))
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def read_index():
    path = os.path.join(static_dir, "index.html")
    return FileResponse(path)

@app.get("/frontend")
async def read_index_frontend():
    """Frontend 分支的前端页面"""
    path = os.path.join(static_dir, "index.html")
    return FileResponse(path)

def format_sse(data: dict) -> str:
    """Safely format SSE data using chr codes for newlines to avoid physical line break issues"""
    json_data = json.dumps(data)
    n = chr(10)
    return "data: " + json_data + n + n

@app.get("/opencode/list_session_files")
async def list_session_files(sid: str):
    session_dir = os.path.join(WORKSPACE_BASE, sid)
    if not os.path.exists(session_dir):
        return {"files": []}
    
    files = []
    for root, dirs, filenames in os.walk(session_dir):
        for filename in filenames:
            rel_path = os.path.relpath(os.path.join(root, filename), session_dir)
            url_path = (sid + "/" + rel_path).replace(os.sep, "/")
            files.append({
                "name": rel_path,
                "path": url_path
            })
    return {"files": files}

@app.get("/opencode/get_file_content")
async def get_file_content(path: str):
    full_path = os.path.abspath(os.path.join(WORKSPACE_BASE, path))
    if not full_path.startswith(WORKSPACE_BASE):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    ext = os.path.splitext(full_path)[1].lower()
    if ext in ['.png', '.jpg', '.jpeg', '.gif', '.pdf', '.html', '.htm', '.svg']:
        return FileResponse(full_path)
    
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content, "filename": os.path.basename(full_path), "type": "text"}
    except Exception as e:
        return {"content": f"Error reading file: {str(e)}", "type": "error"}

@app.get("/opencode/get_log")
async def get_log(sid: str, offset: int = 0):
    """
    Get execution log for a specific session.
    offset: The byte offset to start reading from.
    Returns: {"content": "...", "next_offset": 123, "status": "running/completed"}
    """
    session_dir = os.path.join(WORKSPACE_BASE, sid)
    log_file = os.path.join(session_dir, "run.log")
    
    if not os.path.exists(log_file):
        return {"content": "", "next_offset": 0, "status": "unknown"}
    
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            f.seek(offset)
            content = f.read()
            next_offset = f.tell()
            
        # Check if process is still running (simple check via status file if exists)
        status = "running"
        status_file = os.path.join(session_dir, "status.txt")
        if os.path.exists(status_file):
            with open(status_file, "r", encoding="utf-8") as f:
                status = f.read().strip()
                
        return {"content": content, "next_offset": next_offset, "status": status}
    except Exception as e:
        logger.error(f"Error reading log file: {e}")
        return {"content": "", "next_offset": offset, "status": "error"}

# Global Session Manager
class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}

    async def create_session(self, sid: str, prompt: str):
        if sid in self.sessions:
            return self.sessions[sid]
        
        self.sessions[sid] = {
            "queues": [],  # List of queues for connected clients
            "status": "starting",
            "process": None
        }
        
        # Start background task
        asyncio.create_task(self._run_process(sid, prompt))
        return self.sessions[sid]

    async def _run_process(self, sid: str, prompt: str):
        session_dir = os.path.join(WORKSPACE_BASE, sid)
        os.makedirs(session_dir, exist_ok=True)
        log_file = os.path.join(session_dir, "run.log")
        status_file = os.path.join(session_dir, "status.txt")

        # Init logs
        with open(status_file, "w", encoding="utf-8") as f:
            f.write("running")
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(f"Session started: {sid}\n")

        try:
            # Use script to fake a TTY, forcing unbuffered output
            # We must quote the prompt safely
            safe_prompt = shlex.quote(prompt)
            # Ensure PATH includes bun location
            path_env = "/root/.bun/bin:/usr/local/bin:/usr/local/sbin:/usr/sbin:/usr/bin:/sbin:/bin"
            
            # Construct the inner command
            inner_cmd = f"opencode run --model new-api/gemini-3-flash-preview --format json {safe_prompt}"
            
            # Wrap with script
            cmd = ["script", "-q", "-c", inner_cmd, "/dev/null"]
            
            env = {**os.environ}
            env["PATH"] = path_env
            env["FORCE_COLOR"] = "1"
            
            # Use config_host directly as it's verified to work
            patched_config = "/app/opencode/config_host/opencode.json"
            if os.path.exists(patched_config):
                env["OPENCODE_CONFIG_FILE"] = patched_config

            logger.info(f"Starting process for {sid} with command: {cmd}")
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=session_dir,
                env=env
            )
            
            if sid in self.sessions:
                self.sessions[sid]["process"] = process
                self.sessions[sid]["status"] = "running"

            async for line in process.stdout:
                decoded = line.decode(errors='ignore').strip()
                if decoded:
                    # Write to file
                    with open(log_file, "a", encoding="utf-8") as f:
                        f.write(decoded + "\n")
                    
                    # Broadcast to queues
                    if sid in self.sessions:
                        for q in self.sessions[sid]["queues"]:
                            await q.put(decoded)

            await process.wait()
            
            with open(status_file, "w", encoding="utf-8") as f:
                f.write("completed")
                
            # Notify completion
            if sid in self.sessions:
                self.sessions[sid]["status"] = "completed"
                # Keep session in memory for a while? Or just let it be.
                # Remove queues but keep status?
                
        except Exception as e:
            logger.error(f"Process error for {sid}: {e}")
            with open(status_file, "w", encoding="utf-8") as f:
                f.write("error")
            if sid in self.sessions:
                self.sessions[sid]["status"] = "error"

    async def attach(self, sid: str):
        if sid not in self.sessions:
            return None
        
        q = asyncio.Queue()
        self.sessions[sid]["queues"].append(q)
        return q

    def detach(self, sid: str, q: asyncio.Queue):
        if sid in self.sessions and q in self.sessions[sid]["queues"]:
            self.sessions[sid]["queues"].remove(q)

session_manager = SessionManager()

async def run_agent(prompt: str, sid: str):
    """
    Bridge to the official opencode CLI with Manus-level SSE extensions
    """
    session_dir = os.path.join(WORKSPACE_BASE, sid)
    
    # Ensure session exists or create new
    is_new = sid not in session_manager.sessions
    await session_manager.create_session(sid, prompt)
    
    # Attach listener
    queue = await session_manager.attach(sid)
    
    async def event_generator():
        logger.info(f"Manus-Integrated Agent session attached: {sid}")
        
        # 1. Initialize Manus-style phases
        yield format_sse({
            "type": "phases_init",
            "phases": [
                {"number": 1, "title": "Analyzing Request", "status": "active"},
                {"number": 2, "title": "Executing Task", "status": "pending"},
                {"number": 3, "title": "Summarizing Results", "status": "pending"}
            ]
        })

        # 2. Catch-up from log file
        log_file = os.path.join(session_dir, "run.log")
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                             # Process historical line same as new line
                             async for event in process_log_line(line):
                                 yield event
            except Exception as e:
                logger.error(f"Error reading history: {e}")

        # 3. Stream new events
        last_activity = asyncio.get_running_loop().time()
        
        try:
            while True:
                try:
                    # Wait for output
                    text = await asyncio.wait_for(queue.get(), timeout=1.0)
                    last_activity = asyncio.get_running_loop().time()
                    
                    async for event in process_log_line(text):
                        yield event
                        
                except asyncio.TimeoutError:
                    # Check status
                    session = session_manager.sessions.get(sid)
                    if session and session["status"] in ["completed", "error"] and queue.empty():
                        if session["status"] == "completed":
                            yield format_sse({"type": "phase_update", "number": 3, "status": "completed"})
                            yield format_sse({"type": "file_update", "sid": sid})
                        break
                    
                    # Heartbeat
                    if asyncio.get_running_loop().time() - last_activity > 15:
                        yield format_sse({"type": "ping", "timestamp": str(asyncio.get_running_loop().time())})
                        last_activity = asyncio.get_running_loop().time()
                    continue
                    
        finally:
            session_manager.detach(sid, queue)
            yield format_sse({"type": "status", "value": "done"})

    return event_generator

def map_tool_to_type(tool_name: str) -> str:
    """Map internal tool names to frontend display types"""
    tool = tool_name.lower()
    
    if "read" in tool:
        return "read"
    if "write" in tool or "save" in tool or "create" in tool:
        return "write"
    if "bash" in tool or "sh" == tool or "shell" in tool:
        return "bash"
    if "terminal" in tool or "command" in tool or "cmd" in tool or "run" in tool:
        return "terminal"
    if "grep" in tool or "search" in tool and "web" not in tool and "google" not in tool:
        return "grep"
    if "browser" in tool or "click" in tool or "visit" in tool or "scroll" in tool:
        return "browser"
    if "web" in tool or "google" in tool:
        return "web_search"
    if "edit" in tool or "replace" in tool:
        return "file_editor"
        
    return "file_editor"  # Default fallback

async def process_log_line(text: str):
    # Try to parse as JSON if it looks like one
    if text.startswith("{") and text.endswith("}"):
        try:
            event = json.loads(text)
            event_type = event.get("type")
            
            if event_type == "step_start":
                yield format_sse({"type": "phase_update", "number": 2, "status": "active"})
            
            elif event_type == "tool_use":
                part = event.get("part", {})
                tool_name = part.get("tool", "unknown")
                state = part.get("state", {})
                status = state.get("status")
                output = state.get("output", "")
                
                # Map to standard type
                display_type = map_tool_to_type(tool_name)
                
                # Send as tool_event for the enhanced panel
                yield format_sse({
                    "type": "tool_event", 
                    "data": {
                        "type": "tool",  # Keep generic 'tool' type for frontend logic
                        "tool": display_type,  # Use mapped type as tool name for icon lookup
                        "status": status,
                        "output": output
                    }
                })
                
                # If there's output, also send it as a chunk for visibility
                if output:
                    display_text = f"\n`{tool_name}` output:\n{output}\n"
                    yield format_sse({"type": "answer_chunk", "text": display_text})


            elif event_type == "text":
                chunk = event.get("part", {}).get("text", "")
                if chunk:
                    yield format_sse({"type": "answer_chunk", "text": chunk})
            
            elif event_type == "error":
                err_msg = event.get("message", "Unknown error")
                yield format_sse({"type": "tool_event", "data": {"type": "error", "content": err_msg}})
            
            return
        except Exception as json_err:
            pass

    # Fallback text parsing for Thought and other non-JSON markers
    thought_match = re.search(r"(?:🤔\s*Thought:|Thought:|Thought\s*>\s*|思考[:：])\s*(.*)", text, re.IGNORECASE)
    if thought_match:
        content = thought_match.group(1).strip()
        if content:
            yield format_sse({
                "type": "tool_event", 
                "data": {"type": "thought", "content": content}
            })
            yield format_sse({"type": "phase_update", "number": 2, "status": "active"})
        return
    
    if not text.startswith("{"):
        # Skip help messages, options, or other noise
        noise_keywords = ["opencode run", "options:", "positionals:", "message  message to send", "run opencode with"]
        if not any(x in text.lower() for x in noise_keywords):
            yield format_sse({"type": "answer_chunk", "text": text + " "})

@app.get("/opencode/run_sse")
async def run_sse(prompt: str, sid: str | None = None):
    if not sid: sid = str(uuid.uuid4())
    generator_func = await run_agent(prompt, sid)
    return StreamingResponse(generator_func(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
