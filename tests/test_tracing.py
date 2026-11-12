import json
import os
from types import SimpleNamespace

os.environ["LANGFUSE_TRACING_ENABLED"] = "false"

from agent import tracing  # noqa: E402

KEY = "sk-abcdefghijklmnopqrstuvwx"


def test_json_attribute_is_redacted_inside_the_string():
    value = json.dumps({"messages": [{"role": "user", "content": f"API_KEY={KEY}\"}}"}]})
    out = tracing._redact_attribute(value)
    assert KEY not in out
    assert json.loads(out)["messages"][0]["role"] == "user"  # still valid JSON


def test_plain_and_sequence_attributes_are_redacted():
    assert KEY not in tracing._redact_attribute(f"token {KEY}")
    assert tracing._redact_attribute(("ok", KEY)) == ("ok", "[REDACTED]")


def test_clean_attributes_are_left_alone():
    value = json.dumps({"a": 1}, indent=2)
    assert tracing._redact_attribute(value) is value
    assert tracing._redact_attribute(42) == 42


def test_mask_spans_patches_only_spans_with_secrets():
    clean = SimpleNamespace(attributes={"langfuse.observation.input": '"hello"'})
    dirty = SimpleNamespace(attributes={"langfuse.observation.output": json.dumps(f"here: {KEY}"), "n": 3})
    result = tracing.mask_spans(params=SimpleNamespace(spans={"c": clean, "d": dirty}))
    assert list(result.span_patches) == ["d"]
    patched = result.span_patches["d"].set_attributes
    assert set(patched) == {"langfuse.observation.output"}
    assert KEY not in patched["langfuse.observation.output"]


def test_mask_spans_returns_none_when_nothing_changes():
    clean = SimpleNamespace(attributes={"langfuse.observation.input": '"hello"'})
    assert tracing.mask_spans(params=SimpleNamespace(spans={"c": clean})) is None


def test_disabled_turn_adds_trace_attributes_but_no_handler():
    turn = tracing.Turn("chat-meta", "hi", session_id="s1", client_id="c1", tags=["meta"])
    config = turn.config("answer-question", configurable={"thread_id": "s1"}, callbacks=["logger"])
    assert config["callbacks"] == ["logger"]
    assert config["run_name"] == "answer-question"
    assert config["metadata"]["langfuse_session_id"] == "s1"
    assert config["metadata"]["langfuse_user_id"] == "c1"
    turn.end("answer")  # no-op without a root observation
