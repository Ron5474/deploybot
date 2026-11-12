import logging
import os

from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent.agent import agent, run_with_reflection, run_with_chaining, run_with_meta_prompting, llm, ToolLogger, MODEL_NAME
from agent.tracing import Turn
from agent.prompts import CHECKLIST_PROMPT
from agent.guardrail import redact_secrets, StreamRedactor
from langchain_core.messages import HumanMessage
from db.conversations import save_message, get_all_sessions, get_session_messages, delete_session, delete_last_exchange

logger = logging.getLogger(__name__)

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


def start_turn(request, strategy, endpoint):
    return Turn(
        f"chat-{strategy}",
        request.message,
        session_id=request.session_id,
        client_id=request.client_id,
        tags=[strategy],
        metadata={"endpoint": endpoint, "strategy": strategy, "model": MODEL_NAME},
    )


def run_traced(turn, run, request):
    """Run one non-streaming strategy under `turn` and return the redacted answer."""
    try:
        raw = run(request.message, request.session_id, request.client_id, turn=turn)
    except Exception as e:
        turn.end(error=e)
        raise
    answer = redact_secrets(raw)
    turn.end(answer, metadata={"output_redacted": answer != raw})
    return answer


@app.post("/chat")
def chat(request: ChatRequest):
    def generate():
        from langchain_core.messages import AIMessageChunk, AIMessage
        redactor = StreamRedactor()
        turn = start_turn(request, "regular", "/chat")
        raw = ""
        try:
            for chunk, _ in agent.stream(
                {"messages": [("human", request.message)]},
                stream_mode="messages",
                config=turn.config("run-agent", configurable={"thread_id": request.session_id}, callbacks=[ToolLogger()]),
            ):
                if isinstance(chunk, (AIMessageChunk, AIMessage)) and chunk.content:
                    raw += chunk.content
                    piece = redactor.feed(chunk.content)
                    if piece:
                        yield piece
            tail = redactor.flush()
            if tail:
                yield tail
            save_message(request.session_id, "human", request.message, request.client_id)
            save_message(request.session_id, "assistant", redactor.full_redacted, request.client_id)
            turn.end(redactor.full_redacted, metadata={"output_redacted": redactor.full_redacted != raw})
        except Exception as e:
            turn.end(error=e)
            # Full details stay in the server log; exception text can carry
            # internal URLs, paths or keys, so the client gets a generic message.
            logger.exception("chat stream failed for session %s", request.session_id)
            yield "\n\n[Error: something went wrong while generating the response. Please try again.]"
        finally:
            # Client disconnected mid-stream; close the trace with what was sent.
            turn.end(redactor.full_redacted, metadata={"client_disconnected": True})

    return StreamingResponse(generate(), media_type="text/event-stream")

@app.post("/chat/reflect")
def reflection_chat(request: ChatRequest):
    return {"response": run_traced(start_turn(request, "reflection", "/chat/reflect"), run_with_reflection, request)}

@app.post("/chat/chain")
def chain_chat(request: ChatRequest):
    return {"response": run_traced(start_turn(request, "chaining", "/chat/chain"), run_with_chaining, request)}

@app.post("/chat/meta")
def meta_chat(request: ChatRequest):
    return {"response": run_traced(start_turn(request, "meta", "/chat/meta"), run_with_meta_prompting, request)}


@app.post("/checklist")
def generate_checklist(request: ChecklistRequest):
    turn = Turn("generate-checklist", request.compose, tags=["checklist"],
                metadata={"endpoint": "/checklist", "model": MODEL_NAME})
    prompt = CHECKLIST_PROMPT.format(compose=request.compose)
    try:
        result = llm.invoke([HumanMessage(content=prompt)], config=turn.config("generate-checklist"))
    except Exception as e:
        turn.end(error=e)
        raise
    try:
        import json
        items = json.loads(result.content)
    except Exception:
        items = []
    turn.end(items, metadata={"parsed": bool(items)})
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
