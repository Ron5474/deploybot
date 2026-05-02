import os
import logging
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.globals import set_llm_cache
from langchain_core.callbacks import BaseCallbackHandler
from langchain_community.cache import SQLiteCache
from langgraph.prebuilt import create_react_agent
import sqlite3
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
llm = ChatOpenAI(base_url=MODEL_URL, api_key=MODEL_API_KEY, model=MODEL_NAME)

conn = sqlite3.connect("conversation_history.db", check_same_thread=False)
memory = SqliteSaver(conn)
agent = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT, checkpointer=memory)

SMALL_MODEL_NAME = os.environ["SMALL_MODEL_NAME"]
SMALL_MODEL_API_KEY = os.environ["SMALL_MODEL_API_KEY"]

small_llm = ChatOpenAI(base_url=MODEL_URL, api_key=SMALL_MODEL_API_KEY, model=SMALL_MODEL_NAME)
small_agent = create_react_agent(small_llm, tools, prompt=SYSTEM_PROMPT, checkpointer=memory)


def build_history_messages(session_id):
    history = get_history(session_id)
    messages = []
    for msg in history:
        if msg["role"] == "human":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))
    return messages


def run_with_reflection(user_query, session_id="default", client_id=""):
    history = build_history_messages(session_id)
    result = agent.invoke({"messages": history + [("human", user_query)]}, config={"configurable": {"thread_id": session_id}, "callbacks": [ToolLogger()]})
    initial_response = result["messages"][-1].content

    reflection_prompt = SELF_REFLECTION_PROMPT.format(query=user_query, response=initial_response)
    reflected = llm.invoke([SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=reflection_prompt)])
    save_message(session_id, "human", user_query, client_id)
    save_message(session_id, "assistant", reflected.content, client_id)
    return reflected.content

def run_with_chaining(user_query, session_id="default", client_id=""):
    # Step 1 - Identify the required services
    sys = SystemMessage(content=SYSTEM_PROMPT)
    services_needed = llm.invoke([sys, HumanMessage(content=PROMPT_CHAIN_STEPS["step1"].format(query=user_query))])
    services = services_needed.content

    # Step 2 - Generate individual service blocks
    blocks_needed = llm.invoke([sys, HumanMessage(content=PROMPT_CHAIN_STEPS["step2"].format(services=services, query=user_query))])
    blocks = blocks_needed.content

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
    result = llm.invoke([SystemMessage(content=SYSTEM_PROMPT)] + history + [HumanMessage(content=prompt)])
    save_message(session_id, "human", user_query, client_id)
    save_message(session_id, "assistant", result.content, client_id)
    return result.content
    





