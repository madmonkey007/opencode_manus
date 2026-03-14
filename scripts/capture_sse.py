import asyncio
import json
import os
import time
import uuid

import httpx

API_BASE_URL = os.environ.get("OPENCODE_BASE_URL", "http://localhost:8089/opencode").rstrip("/")
EVENT_BASE_URL = os.environ.get("OPENCODE_SSE_BASE", "http://localhost:4096").rstrip("/")
WORKDIR = os.path.abspath("workspace")
SESSION_ID = f"ses_probe_{uuid.uuid4().hex[:8]}"
LOG_PATH = os.path.abspath(os.path.join("logs", f"sse-capture-{SESSION_ID}.ndjson"))


def now_ts() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


async def create_session(client: httpx.AsyncClient) -> str:
    url = f"{API_BASE_URL}/session"
    params = {"directory": os.path.join(WORKDIR, SESSION_ID), "workspace": SESSION_ID}
    payload = {"title": "SSE probe"}
    r = await client.post(url, params=params, json=payload)
    r.raise_for_status()
    data = r.json()
    return data.get("id") or data.get("session_id") or data.get("sessionID")


async def send_message(client: httpx.AsyncClient, server_session_id: str) -> None:
    url = f"{API_BASE_URL}/session/{server_session_id}/message"
    params = {"directory": os.path.join(WORKDIR, SESSION_ID), "workspace": SESSION_ID}
    payload = {
        "messageID": f"msg_{uuid.uuid4().hex[:8]}",
        "message_id": None,
        "model": {"providerID": "openai", "modelID": "gpt-4.1-mini"},
        "agent": "build",
        "parts": [
            {
                "type": "text",
                "text": "生成一个极简的HTML文件，文件名 index.html，内容是一个带按钮的闹钟页面。",
            }
        ],
    }
    payload["message_id"] = payload["messageID"]
    r = await client.post(url, params=params, json=payload)
    r.raise_for_status()


async def sse_listener(server_session_id: str, stop_after: float = 20.0) -> None:
    base = EVENT_BASE_URL
    params = {"directory": os.path.join(WORKDIR, SESSION_ID), "workspace": SESSION_ID}
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    start = time.time()
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("GET", f"{base}/global/event", params=params) as resp:
            resp.raise_for_status()
            buf: list[str] = []
            async for line in resp.aiter_lines():
                if time.time() - start > stop_after:
                    break
                if line == "":
                    if not buf:
                        continue
                    data_str = "\n".join(buf).strip()
                    buf = []
                    if not data_str or data_str == "[DONE]":
                        continue
                    try:
                        event = json.loads(data_str)
                    except Exception:
                        continue
                    payload = event.get("payload") or event
                    sid = (
                        payload.get("sessionID")
                        or payload.get("session_id")
                        or payload.get("sessionId")
                    )
                    if sid != server_session_id:
                        continue
                    with open(LOG_PATH, "a", encoding="utf-8") as f:
                        f.write(json.dumps({"ts": now_ts(), "event": payload}, ensure_ascii=False) + "\n")
                elif line.startswith("data:"):
                    buf.append(line[5:].lstrip())


async def main() -> None:
    print(f"[capture_sse] API base: {API_BASE_URL}, event base: {EVENT_BASE_URL}")
    async with httpx.AsyncClient(timeout=30.0) as client:
        server_session_id = await create_session(client)

    listener = asyncio.create_task(sse_listener(server_session_id))
    await asyncio.sleep(0.5)
    async with httpx.AsyncClient(timeout=60.0) as client:
        await send_message(client, server_session_id)
    await listener
    print(f"SSE log saved: {LOG_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
