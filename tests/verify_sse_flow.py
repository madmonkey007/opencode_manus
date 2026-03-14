import asyncio
import aiohttp
import json
import time
import sys

BASE_URL = "http://localhost:8088"

async def verify_sse_flow():
    print(f"Connecting to {BASE_URL}...")
    
    async with aiohttp.ClientSession() as session:
        # 1. Create Session
        print("Creating session...")
        async with session.post(f"{BASE_URL}/opencode/session") as resp:
            if resp.status != 200:
                print(f"Failed to create session: {await resp.text()}")
                return
            session_data = await resp.json()
            session_id = session_data["session_id"]
            print(f"Session created: {session_id}")

        # 2. Start SSE listener in background
        print("Starting SSE listener...")
        events_received = []
        stop_event = asyncio.Event()

        async def listen_sse():
            try:
                async with session.get(f"{BASE_URL}/opencode/session/{session_id}/events") as resp:
                    print("SSE Connected!")
                    last_time = time.time()
                    async for line in resp.content:
                        line = line.decode('utf-8').strip()
                        if line.startswith("data: "):
                            data_str = line[6:]
                            try:
                                data = json.loads(data_str)
                                current_time = time.time()
                                interval = (current_time - last_time) * 1000
                                last_time = current_time
                                
                                event_type = data.get("type", "unknown")
                                events_received.append({
                                    "type": event_type,
                                    "interval": interval,
                                    "content_len": len(str(data))
                                })
                                
                                # Print event info (type + interval)
                                print(f"Event: {event_type:<15} | Interval: {interval:>6.1f}ms | Len: {len(str(data))}")

                                if event_type == "ping":
                                    continue
                                    
                            except json.JSONDecodeError:
                                pass
                        
                        if stop_event.is_set():
                            break
            except Exception as e:
                print(f"SSE Error: {e}")

        listener_task = asyncio.create_task(listen_sse())

        # 3. Send Message
        print("\nSending task: 'Calculate Fibonacci first 50 numbers and explain algorithm'...")
        prompt = "Calculate Fibonacci first 50 numbers and explain algorithm"
        async with session.post(f"{BASE_URL}/opencode/session/{session_id}/message", json={"prompt": prompt}) as resp:
            if resp.status != 200:
                print(f"Failed to send message: {await resp.text()}")
                return
            print("Message sent successfully. Waiting for events...")

        # 4. Wait for a while to collect events
        await asyncio.sleep(15)
        stop_event.set()
        try:
            await asyncio.wait_for(listener_task, timeout=2)
        except asyncio.TimeoutError:
            pass

        # 5. Analyze results
        print("\n--- Analysis ---")
        total_events = len(events_received)
        print(f"Total events received: {total_events}")
        
        thought_events = [e for e in events_received if e["type"] in ["thought", "call_tool", "tool_output"]]
        content_events = [e for e in events_received if e["type"] == "content"]
        
        print(f"Thought/Tool events: {len(thought_events)}")
        print(f"Content events: {len(content_events)}")
        
        if len(content_events) > 5:
            avg_interval = sum(e["interval"] for e in content_events) / len(content_events)
            print(f"Average content interval: {avg_interval:.2f}ms")
            
            if avg_interval < 10:
                print("⚠️  WARNING: Interval too short! Might be non-streaming (buffered).")
            else:
                print("✅  SUCCESS: Interval looks like streaming.")
        else:
            print("⚠️  WARNING: Not enough content events to analyze streaming.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(verify_sse_flow())
