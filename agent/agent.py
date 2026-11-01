import os
import logging
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.globals import set_llm_cache
from langchain_core.callbacks import BaseCallbackHandler
from langchain_community.cache import SQLiteCache
from langchain.agents import create_agent
import sqlite3
import uuid
from langgraph.checkpoint.sqlite import SqliteSaver

logging.basicConfig(level=logging.INFO, format="%(asctime)s [TOOL] %(message)s")
logger = logging.getLogger(__name__)

class ToolLogger(BaseCallbackHandler):
    def on_tool_start(self, serialized, input_str, **kwargs):
        logger.info(f"{serialized['name']} ← {str(input_str)[:120]}")

    def on_tool_end(self, output, **kwargs):
        logger.info(f"→ {str(output)[:120]}")

from tools.db_tool import query_app_db
from tools.web_search import web_search
from tools.cve_tool import retrieve_cve
from rag.retriever import get_info_from_vector_db
from agent.prompts import SYSTEM_PROMPT, SELF_REFLECTION_PROMPT, PROMPT_CHAIN_STEPS, META_PROMPT
from db.conversations import get_history, save_message


load_dotenv()

MODEL_URL = os.environ["MODEL_BASE_URL"]
MODEL_API_KEY = os.environ["MODEL_API_KEY"]
MODEL_NAME = os.environ["MODEL_NAME"]


tools = [query_app_db, web_search, retrieve_cve, get_info_from_vector_db]

if not os.environ.get("DISABLE_CACHE"):
    set_llm_cache(SQLiteCache(database_path=".langchain_cache.db"))
llm = ChatOpenAI(base_url=MODEL_URL, api_key=MODEL_API_KEY, model=MODEL_NAME, timeout=60, max_retries=1)

conn = sqlite3.connect("conversation_history.db", check_same_thread=False)
memory = SqliteSaver(conn)
agent = create_agent(llm, tools, system_prompt=SYSTEM_PROMPT, checkpointer=memory)

SMALL_MODEL_NAME = os.environ["SMALL_MODEL_NAME"]
SMALL_MODEL_API_KEY = os.environ["SMALL_MODEL_API_KEY"]

small_llm = ChatOpenAI(base_url=MODEL_URL, api_key=SMALL_MODEL_API_KEY, model=SMALL_MODEL_NAME, timeout=60, max_retries=1)
small_agent = create_agent(small_llm, tools, system_prompt=SYSTEM_PROMPT, checkpointer=memory)


def build_history_messages(session_id):
    history = get_history(session_id)
    messages = []
    for msg in history:
        if msg["role"] == "human":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))
    return messages


# Cap on tool output handed to the reflection reviewer; web search and README
# chunks can run to tens of thousands of characters.
MAX_EVIDENCE_CHARS = 30_000


def tool_evidence(messages):
    """Tool outputs from the latest turn (everything after the last human
    message), formatted for the reviewer."""
    last_human = max((i for i, m in enumerate(messages) if m.type == "human"), default=-1)
    outputs = [m for m in messages[last_human + 1:] if m.type == "tool"]
    if not outputs:
        return "(no tools were called)"
    text = "\n\n".join(f"[{m.name}]\n{m.content}" for m in outputs)
    return text[:MAX_EVIDENCE_CHARS]


def run_with_reflection(user_query, session_id="default", client_id=""):
    history = build_history_messages(session_id)
    result = agent.invoke({"messages": history + [("human", user_query)]}, config={"configurable": {"thread_id": session_id}, "callbacks": [ToolLogger()]})
    initial_response = result["messages"][-1].content

    # The reviewer has no tools, so it gets the draft's tool outputs as
    # evidence; without them it strips CVEs and versions it can't verify.
    reflection_prompt = SELF_REFLECTION_PROMPT.format(query=user_query, response=initial_response, evidence=tool_evidence(result["messages"]))
    reflected = llm.invoke([SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=reflection_prompt)])
    save_message(session_id, "human", user_query, client_id)
    save_message(session_id, "assistant", reflected.content, client_id)
    return reflected.content

def run_with_chaining(user_query, session_id="default", client_id=""):
    # Step 1 - Identify the required services
    sys = SystemMessage(content=SYSTEM_PROMPT)
    services_needed = llm.invoke([sys, HumanMessage(content=PROMPT_CHAIN_STEPS["step1"].format(query=user_query))])
    services = services_needed.content

    # Step 2 - Generate individual service blocks. Runs through the agent so it
    # can look up current image tags and env vars. Its own throwaway thread
    # keeps the step prompt out of the user's conversation memory.
    blocks_needed = agent.invoke(
        {"messages": [("human", PROMPT_CHAIN_STEPS["step2"].format(services=services, query=user_query))]},
        config={"configurable": {"thread_id": f"{session_id}-chain-{uuid.uuid4().hex[:8]}"}, "callbacks": [ToolLogger()]},
    )
    blocks = blocks_needed["messages"][-1].content

    # Step 3 - Combine into full compose file
    compose = llm.invoke([sys, HumanMessage(content=PROMPT_CHAIN_STEPS["step3"].format(service_blocks=blocks))])
    compose_file = compose.content

    # Step 4 - Security Hardening
    hardened = llm.invoke([sys, HumanMessage(content=PROMPT_CHAIN_STEPS["step4"].format(compose_file=compose_file))])
    save_message(session_id, "human", user_query, client_id)
    save_message(session_id, "assistant", hardened.content, client_id)
    return hardened.content

def run_with_meta_prompting(user_query, session_id="default", client_id=""):
    history = build_history_messages(session_id)
    prompt = META_PROMPT.format(query=user_query)
    result = agent.invoke({"messages": history + [("human", prompt)]}, config={"configurable": {"thread_id": session_id}, "callbacks": [ToolLogger()]})
    answer = result["messages"][-1].content
    save_message(session_id, "human", user_query, client_id)
    save_message(session_id, "assistant", answer, client_id)
    return answer
    





