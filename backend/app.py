import os

from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent.agent import agent, run_with_reflection, run_with_chaining, run_with_meta_prompting, llm, ToolLogger
from agent.prompts import CHECKLIST_PROMPT
from langchain_core.messages import HumanMessage
from db.conversations import save_message, get_all_sessions, get_session_messages, delete_session, delete_last_exchange

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    session_id: str
    client_id: str = ""

class ChecklistRequest(BaseModel):
    compose: str


@app.post("/chat")
def chat(request: ChatRequest):
    def generate():
        from langchain_core.messages import AIMessageChunk, AIMessage
        full_response = []
        try:
            for chunk, _ in agent.stream(
                {"messages": [("human", request.message)]},
                stream_mode="messages",
                config={"configurable": {"thread_id": request.session_id}, "callbacks": [ToolLogger()]}
            ):
                if isinstance(chunk, (AIMessageChunk, AIMessage)) and chunk.content:
                    full_response.append(chunk.content)
                    yield chunk.content
            save_message(request.session_id, "human", request.message, request.client_id)
            save_message(request.session_id, "assistant", "".join(full_response), request.client_id)
        except Exception as e:
            yield f"\n\n[Error: {e}]"

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/chat/reflect")
def reflection_chat(request: ChatRequest):
    res = run_with_reflection(request.message, request.session_id, request.client_id)
    return {"response": res}

@app.post("/chat/chain")
def chain_chat(request: ChatRequest):
    res = run_with_chaining(request.message, request.session_id, request.client_id)
    return {"response": res}

@app.post("/chat/meta")
def meta_chat(request: ChatRequest):
    res = run_with_meta_prompting(request.message, request.session_id, request.client_id)
    return {"response": res}


@app.post("/checklist")
def generate_checklist(request: ChecklistRequest):
    prompt = CHECKLIST_PROMPT.format(compose=request.compose)
    result = llm.invoke([HumanMessage(content=prompt)])
    try:
        import json
        items = json.loads(result.content)
    except Exception:
        items = []
    return {"items": items}

@app.get("/conversations")
def list_conversations(client_id: str = Query(default="")):
    return get_all_sessions(client_id)

@app.get("/conversations/{session_id}")
def get_conversation(session_id):
    return get_session_messages(session_id)

@app.delete("/conversations/{session_id}/last")
def remove_last_exchange(session_id):
    delete_last_exchange(session_id)
    return {"status": "deleted"}

@app.delete("/conversations/{session_id}")
def remove_conversation(session_id):
    delete_session(session_id)
    return {"status": "deleted"}


# Serve React build — must be mounted AFTER all API routes
_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(_dist):
    app.mount("/", StaticFiles(directory=_dist, html=True), name="static")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
