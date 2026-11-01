import os

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

# agent.agent reads these at import time; the fakes below mean no request is
# ever sent, so placeholder values are enough.
for var in ("MODEL_BASE_URL", "MODEL_API_KEY", "MODEL_NAME", "SMALL_MODEL_NAME", "SMALL_MODEL_API_KEY"):
    os.environ.setdefault(var, "test")
os.environ.setdefault("DISABLE_CACHE", "1")

import agent.agent as agent_mod  # noqa: E402


class FakeAgent:
    """Records each invoke and replies with a fixed message list."""

    def __init__(self, reply_messages):
        self.reply_messages = reply_messages
        self.calls = []

    def invoke(self, inputs, config=None):
        self.calls.append((inputs, config))
        return {"messages": self.reply_messages}


class FakeLLM:
    def __init__(self, reply="final"):
        self.reply = reply
        self.prompts = []

    def invoke(self, messages):
        self.prompts.append(messages)
        return AIMessage(content=self.reply)


@pytest.fixture
def no_db(monkeypatch):
    monkeypatch.setattr(agent_mod, "save_message", lambda *a, **k: None)
    monkeypatch.setattr(agent_mod, "build_history_messages", lambda session_id: [])


def cve_turn():
    return [
        HumanMessage(content="Does Immich have any recent CVEs?"),
        AIMessage(content=""),
        ToolMessage(content='[{"id": "CVE-2026-12345"}]', name="retrieve_cve", tool_call_id="1"),
        AIMessage(content="Yes: CVE-2026-12345."),
    ]


def test_tool_evidence_uses_only_latest_turn():
    messages = [
        HumanMessage(content="old question"),
        ToolMessage(content="OLD TOOL OUTPUT", name="web_search", tool_call_id="0"),
        AIMessage(content="old answer"),
    ] + cve_turn()
    evidence = agent_mod.tool_evidence(messages)
    assert "CVE-2026-12345" in evidence
    assert "[retrieve_cve]" in evidence
    assert "OLD TOOL OUTPUT" not in evidence


def test_tool_evidence_without_tools():
    assert agent_mod.tool_evidence([HumanMessage(content="hi"), AIMessage(content="hello")]) == "(no tools were called)"


def test_tool_evidence_is_capped():
    big = [HumanMessage(content="q"), ToolMessage(content="x" * 100_000, name="web_search", tool_call_id="1")]
    assert len(agent_mod.tool_evidence(big)) == agent_mod.MAX_EVIDENCE_CHARS


def test_reflection_reviewer_sees_tool_outputs(monkeypatch, no_db):
    monkeypatch.setattr(agent_mod, "agent", FakeAgent(cve_turn()))
    llm = FakeLLM()
    monkeypatch.setattr(agent_mod, "llm", llm)

    assert agent_mod.run_with_reflection("Does Immich have any recent CVEs?", "s1") == "final"
    review_prompt = llm.prompts[0][-1].content
    assert "Yes: CVE-2026-12345." in review_prompt          # the draft
    assert '[{"id": "CVE-2026-12345"}]' in review_prompt    # the raw tool output


def test_meta_prompting_runs_through_agent(monkeypatch, no_db):
    fake = FakeAgent(cve_turn())
    monkeypatch.setattr(agent_mod, "agent", fake)
    llm = FakeLLM()
    monkeypatch.setattr(agent_mod, "llm", llm)

    assert agent_mod.run_with_meta_prompting("Does Immich have any recent CVEs?", "s1") == "Yes: CVE-2026-12345."
    assert llm.prompts == []
    inputs, config = fake.calls[0]
    assert "Does Immich have any recent CVEs?" in inputs["messages"][-1][1]
    assert config["configurable"]["thread_id"] == "s1"


def test_chaining_step2_uses_agent_on_separate_thread(monkeypatch, no_db):
    fake = FakeAgent([HumanMessage(content="step2"), AIMessage(content="BLOCKS")])
    monkeypatch.setattr(agent_mod, "agent", fake)
    llm = FakeLLM()
    monkeypatch.setattr(agent_mod, "llm", llm)

    agent_mod.run_with_chaining("Gitea with PostgreSQL", "s1")
    assert len(fake.calls) == 1                 # step 2 only
    assert len(llm.prompts) == 3                # steps 1, 3, 4
    thread_id = fake.calls[0][1]["configurable"]["thread_id"]
    assert thread_id.startswith("s1-chain-")    # not the user's own thread
    assert "BLOCKS" in llm.prompts[1][-1].content  # step 3 got step 2's output
