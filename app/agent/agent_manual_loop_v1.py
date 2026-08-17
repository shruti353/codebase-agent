"""
V1 of the agent — a manual, hand-written tool-calling loop (no framework).
Superseded by graph_agent.py, which reimplements the same logic using
LangGraph's StateGraph. Kept here as a reference showing the underlying
mechanics that LangGraph abstracts away — see graph_agent.py for the
version actually used by the FastAPI app.
"""

from dotenv import load_dotenv
load_dotenv()

import os, json
from groq import Groq, BadRequestError


from qdrant_client import QdrantClient
from app.storage.db import get_connection, get_callers, get_function_source
from app.storage.vector_store import search_code

client = Groq(api_key=os.environ["GROQ_API_KEY"])
qdrant = QdrantClient(host="localhost", port=6333)
conn = get_connection()

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Semantically search the codebase for functions or classes related to a query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for, in plain English"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_function_source",
            "description": "Get the full source code of a function or class, given its exact name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "function_name": {"type": "string", "description": "Exact name of the function or class"},
                },
                "required": ["function_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_callers",
            "description": "Find every function that calls the given function name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "function_name": {"type": "string", "description": "Exact name of the function to check"},
                },
                "required": ["function_name"],
            },
        },
    },
]

def call_tool(name: str, args: dict):
    if name=="search_code":
        results= search_code(qdrant, args["query"],top_k=3)
        return [{"name": r.payload["name"], "file": r.payload["file"], "score": r.score} for r in results]
    elif name=="get_function_source":
        return get_function_source(conn, args["function_name"])
    elif name=="get_callers":
        return get_callers(conn, args["function_name"])
    return f"Unknown tool: {name}"



def ask(question: str, max_turns: int = 5):
    SYSTEM_PROMPT = (
    "You are a codebase assistant. You must answer only using information "
    "returned by tools — never from general knowledge. When you need "
    "information, call exactly one tool using the API's tool-calling "
    "mechanism. Never write a tool call as text. Respond with plain text "
    "only once you have enough tool results to answer."
    )
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    for _ in range(max_turns):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=0,
            )
        except BadRequestError as e:
            print(f"  [warning] tool call generation failed, retrying with a nudge: {e}")
            messages.append({
                "role": "user",
                "content": "Your last response was invalid. Call exactly one tool properly, or answer in plain text only — do not mix the two.",
            })
            continue

        message = response.choices[0].message

        if not message.tool_calls:
            return message.content

        assistant_message = {
            "role": "assistant",
            "content": message.content or "",
        }

        if message.tool_calls:
            assistant_message["tool_calls"] = []

            for tc in message.tool_calls:
                assistant_message["tool_calls"].append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            })

        messages.append(assistant_message)

        for tool_call in message.tool_calls:
            args = json.loads(tool_call.function.arguments)
            result = call_tool(tool_call.function.name, args)
            print(f"  [tool call] {tool_call.function.name}({args}) -> {result}")

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })

    return "Ran out of turns without a final answer."

if __name__ == "__main__":
    answer = ask("What does the factorial function do?")
    print("\nFinal answer:", answer)