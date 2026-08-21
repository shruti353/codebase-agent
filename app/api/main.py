import json
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, HTMLResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.graph_agent import app as agent_graph, SYSTEM_PROMPT

api= FastAPI(title="Codebase Agent API", description="API for the Codebase Agent", version="0.1")

class ChatRequest(BaseModel):
    question:str

import traceback

def event_stream(question: str):
    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=question)]

    try:
        for step in agent_graph.stream(
            {"messages": messages},
            config={"recursion_limit": 15},
            stream_mode="values",
        ):
            last_msg = step["messages"][-1]
            msg_type = getattr(last_msg, "type", None)

            if msg_type in ("human", "system"):
                continue
            elif getattr(last_msg, "tool_calls", None):
                for tc in last_msg.tool_calls:
                    payload = {"type": "tool_call", "name": tc["name"], "args": tc["args"]}
                    yield f"data: {json.dumps(payload)}\n\n"
            elif msg_type == "tool":
                payload = {"type": "tool_result", "content": str(last_msg.content)[:300]}
                yield f"data: {json.dumps(payload)}\n\n"
            else:
                payload = {"type": "final", "content": last_msg.content}
                yield f"data: {json.dumps(payload)}\n\n"
    except Exception as e:
        print("AGENT ERROR:", traceback.format_exc())  # <- this is what will show in Render logs
        payload = {"type": "final", "content": f"Error: {type(e).__name__}: {str(e)}"}
        yield f"data: {json.dumps(payload)}\n\n"
        
            
@api.post("/chat")
def chat(req: ChatRequest):
    return StreamingResponse(event_stream(req.question),media_type="text/event-stream")

@api.get("/health")
def health():
    return {"status": "ok"}

@api.get("/", response_class=HTMLResponse)
def index():
    return """
<!DOCTYPE html>
<html>
<head><title>Codebase Agent</title></head>
<body style="font-family: monospace; max-width: 700px; margin: 40px auto;">
  <h2>Codebase Agent</h2>
  <input id="q" style="width: 80%;" placeholder="Ask about the codebase..." />
  <button onclick="ask()">Ask</button>
  <pre id="out" style="white-space: pre-wrap; background: #111; color: #0f0; padding: 10px; min-height: 200px;"></pre>

<script>
async function ask() {
  const question = document.getElementById("q").value;
  const out = document.getElementById("out");
  out.textContent = "";

  const response = await fetch("/chat", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({question})
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const {value, done} = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, {stream: true});

    let parts = buffer.split("\\n\\n");
    buffer = parts.pop();

    for (const part of parts) {
      if (!part.startsWith("data: ")) continue;
      const data = JSON.parse(part.slice(6));

      if (data.type === "tool_call") {
        out.textContent += `[calling ${data.name}(${JSON.stringify(data.args)})]\\n`;
      } else if (data.type === "tool_result") {
        out.textContent += `[result] ${data.content}\\n`;
      } else if (data.type === "final") {
        out.textContent += `\\nAnswer: ${data.content}\\n`;
      }
    }
  }
}
</script>
</body>
</html>
"""


