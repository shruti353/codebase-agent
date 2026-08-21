from dotenv import load_dotenv
load_dotenv()

import os
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.storage.db import get_connection, get_callers, get_callees, get_function_source
from app.storage.vector_store import search_code as _search_code

conn= get_connection()

qdrant= QdrantClient(
    url=os.getenv("QDRANT_URL", "http://localhost:6333"),
    api_key=os.getenv("QDRANT_API_KEY"),
)
# ---- Tools: same logic as Day 4, now wrapped with @tool so LangGraph
# can generate their schemas automatically instead of you hand-writing JSON ----

@tool
def search_code(query: str) -> str:
    """Semantically search the codebase for functions or classes related to a query."""
    results = _search_code(qdrant, query, top_k=3)
    if not results:
        return "No matching code found."
    lines = [f"{r.payload['name']} ({r.payload['file']}, score={r.score:.3f})" for r in results]
    return "\n".join(lines)

@tool
def get_source(function_name: str) -> str:
    """Get the full source code of a function or class, given its exact name."""
    return get_function_source(conn, function_name) or f"No function named '{function_name}' found."

@tool
def get_callers_of(function_name: str) -> str:
    """Find every function that calls the given function name."""
    callers = get_callers(conn, function_name)
    if not callers:
        return f"No functions call '{function_name}'."
    return ", ".join(callers)

@tool
def get_callees_of(function_name: str) -> str:
    """Find every function that the given function calls."""
    callees = get_callees(conn, function_name)
    if not callees:
        return f"'{function_name}' does not call any other tracked functions."
    return ", ".join(callees)



tools= [search_code, get_source, get_callers_of, get_callees_of]
llm = ChatGroq(
    model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
    temperature=0,
)

llm_with_tools= llm.bind_tools(tools)


# ---- Graph state: just the running message history ----
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    
def agent_node(state: AgentState):
    response= llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


def should_continue(state: AgentState):
    last_message= state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return END

graph = StateGraph(AgentState)
graph.add_node("agent", agent_node)
graph.add_node("tools",ToolNode(tools))
graph.set_entry_point("agent")
graph.add_conditional_edges("agent", should_continue, {"tools":"tools", END:END})
graph.add_edge("tools","agent")

app=graph.compile()


SYSTEM_PROMPT = """You are a codebase analysis assistant. You have access to both
exact structural data (get_callers_of, get_callees_of) and semantic search
(search_code). Exact structural tools give ground truth — trust their results
completely. Semantic search gives approximate, fuzzy leads — treat matches from
search_code as "possibly related, unverified" and never state them as fact
unless you also confirm the relationship with get_callers_of or get_callees_of
or by reading the actual source with get_source.

When asked what might break from a change, get_callers_of is authoritative:
if it returns no callers, state clearly that nothing is affected — do not add
speculative maybes from search results."""

def ask(question: str):
    result = app.invoke({"messages": [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=question),
    ]})

    for msg in result["messages"]:
        if getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                print(f"  [tool call] {tc['name']}({tc['args']})")
        elif getattr(msg, "type", None) == "tool":
            print(f"  [tool result] {msg.content[:200]}")

    return result["messages"][-1].content


if __name__ == "__main__":
    question = "If I changed what the 'add' function returns, what other functions might break?"
    answer = ask(question)
    print("\nFinal answer:", answer)