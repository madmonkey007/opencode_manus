import asyncio
import json
import logging
import os
import uuid
import time
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from dotenv import load_dotenv

# 加载配置
load_dotenv()

app = FastAPI()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mock_kernel")

# 存储正在运行的任务
# {server_session_id: {"queue": asyncio.Queue, "status": "idle"}}
sessions = {}

@app.post("/session")
async def create_session():
    sid = str(uuid.uuid4())
    sessions[sid] = {"queue": asyncio.Queue(), "status": "idle"}
    logger.info(f"Created mock session: {sid}")
    return {"id": sid}

@app.get("/session")
async def list_sessions():
    return [{"id": s} for s in sessions.keys()]

@app.post("/session/{sid}/prompt_async")
async def prompt_async(sid: str, request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    prompt = data.get("parts", [{}])[0].get("text", "")
    
    if sid not in sessions:
        sessions[sid] = {"queue": asyncio.Queue(), "status": "idle"}
        
    sessions[sid]["status"] = "busy"
    background_tasks.add_task(run_mock_task, sid, prompt)
    return "", 204

@app.get("/session/{sid}/event")
async def session_event(sid: str):
    if sid not in sessions:
        return {"error": "Session not found"}, 404
        
    async def event_generator():
        queue = sessions[sid]["queue"]
        while True:
            event = await queue.get()
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("type") == "session.idle":
                sessions[sid]["status"] = "idle"
                break
                
    return StreamingResponse(event_generator(), media_type="text/event-stream")

async def run_mock_task(sid: str, prompt: str):
    queue = sessions[sid]["queue"]

    # 模拟 AI 思考
    await queue.put({"type": "thought", "text": "我正在为您编写网页闹钟代码..."})
    await asyncio.sleep(1)

    # 模拟写入文件（使用会话隔离的目录）
    session_dir = os.path.join("workspace", sid)
    file_path = os.path.join(session_dir, "clock.html")
    content = """<!DOCTYPE html>
<html>
<head>
    <title>简单闹钟</title>
    <style>
        body { font-family: sans-serif; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; background: #f0f0f0; }
        .clock { font-size: 48px; margin-bottom: 20px; }
        .controls { display: flex; gap: 10px; }
        input { padding: 10px; font-size: 18px; }
        button { padding: 10px 20px; font-size: 18px; cursor: pointer; background: #007bff; color: white; border: none; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="clock" id="clock">00:00:00</div>
    <div class="controls">
        <input type="time" id="alarmTime">
        <button onclick="setAlarm()">设置闹钟</button>
    </div>
    <script>
        function updateClock() {
            const now = new Date();
            document.getElementById('clock').innerText = now.toLocaleTimeString();
            if (window.alarmTime === now.toTimeString().substring(0, 5)) {
                alert("闹钟时间到！");
                window.alarmTime = null;
            }
        }
        setInterval(updateClock, 1000);
        function setAlarm() {
            window.alarmTime = document.getElementById('alarmTime').value;
            alert("闹钟已设置: " + window.alarmTime);
        }
    </script>
</body>
</html>"""

    # 执行真实写入
    os.makedirs(session_dir, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    await queue.put({
        "type": "tool_use", 
        "tool": "write", 
        "input": {"file_path": file_path, "content": "HTML code..."},
        "output": f"Successfully wrote to {file_path}"
    })
    
    await queue.put({"type": "text", "text": "我已经为您创建了一个简单的网页版闹钟，文件保存在 `workspace/clock.html`。"})
    await queue.put({"type": "session.idle"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=4096)
