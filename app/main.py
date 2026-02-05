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

async def run_agent(prompt: str, sid: str):
    """
    Bridge to the official opencode CLI with Manus-level SSE extensions
    """
    session_dir = os.path.join(WORKSPACE_BASE, sid)
    os.makedirs(session_dir, exist_ok=True)
    
    async def event_generator():
        logger.info(f"Manus-Integrated Agent session started: {sid}")
        
        # 1. Initialize Manus-style phases
        yield format_sse({
            "type": "phases_init",
            "phases": [
                {"number": 1, "title": "Analyzing Request", "status": "active"},
                {"number": 2, "title": "Executing Task", "status": "pending"},
                {"number": 3, "title": "Summarizing Results", "status": "pending"}
            ]
        })

        try:
            # Command to run official opencode-ai CLI
            cmd = ["opencode", "run", prompt]
            
            env = {**os.environ, "DISPLAY": ":0"}
            patched_config = "/app/opencode/config/opencode.json"
            if os.path.exists(patched_config):
                env["OPENCODE_CONFIG_FILE"] = patched_config

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=session_dir,
                env=env
            )

            async def handle_stream(stream, queue):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    decoded = line.decode(errors='ignore').strip()
                    if decoded:
                        await queue.put(decoded)

            queue = asyncio.Queue()
            stdout_task = asyncio.create_task(handle_stream(process.stdout, queue))
            stderr_task = asyncio.create_task(handle_stream(process.stderr, queue))

            while True:
                try:
                    text = await asyncio.wait_for(queue.get(), timeout=0.1)
                    if not text: continue
                    
                    # Log parsing for SSE mapping
                    # 1. Thought detection
                    thought_match = re.search(r"(?:🤔\s*Thought:|Thought:|Thought\s+>)\s*(.*)", text, re.IGNORECASE)
                    if thought_match:
                        content = thought_match.group(1).strip()
                        yield format_sse({"type": "tool_event", "data": {"type": "thought", "content": content}})
                        yield format_sse({"type": "phase_update", "number": 2, "status": "active"})
                        continue

                    # 2. Tool activation detection
                    tool_match = re.search(r"(?:🔧\s*(?:Using tool:|Using)|Using tool:|Tool\s+Activate\s+>)\s*([\w\-]+)", text, re.IGNORECASE)
                    if tool_match:
                        t_name = tool_match.group(1).strip()
                        if t_name.lower() != "undefined":
                            yield format_sse({"type": "tool_event", "data": {"type": "activate", "tool": t_name, "status": "running"}})
                            continue
                    
                    # 3. File streaming detection (Manus-level feature)
                    if "writing to" in text.lower() or "updating" in text.lower():
                        yield format_sse({"type": "file_content_append", "content": text + chr(10), "filename": "output.txt"})

                    # 4. File completion detection
                    if any(kw in text.lower() for kw in ["saved", "written", "file created", "creating file", "file >"]):
                        yield format_sse({"type": "file_update", "sid": sid})
                        f_match = re.search(r'(?:File\s+>\s+)?([\w\.\:/\-]+)', text, re.IGNORECASE)
                        fname = f_match.group(1).strip() if f_match else "result"
                        yield format_sse({"type": "answer_chunk", "text": f"📁 Created: **{fname}** "})
                        continue

                    # 5. Output mapping
                    if not any(x in text.lower() for x in ["debug", "info", "trace", "listening on", "started", "positionals:", "options:", "opencode run [message..]"]):
                        yield format_sse({"type": "answer_chunk", "text": text + " "})
                        
                except asyncio.TimeoutError:
                    if process.returncode is not None and queue.empty():
                        break
                    continue

            await process.wait()
            yield format_sse({"type": "phase_update", "number": 3, "status": "completed"})
            yield format_sse({"type": "file_update", "sid": sid})

        except Exception as e:
            logger.error("Kernel bridge error: " + str(e))
            yield format_sse({"type": "tool_event", "data": {"type": "error", "content": "Kernel Error: " + str(e)}})
        
        yield format_sse({"type": "status", "value": "done"})

    return event_generator

@app.get("/opencode/run_sse")
async def run_sse(prompt: str, sid: str | None = None):
    if not sid: sid = str(uuid.uuid4())
    generator_func = await run_agent(prompt, sid)
    return StreamingResponse(generator_func(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
