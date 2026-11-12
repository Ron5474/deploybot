"""Langfuse tracing.

One trace per chat turn, grouped into a Langfuse session per conversation
(session_id) and attributed to the browser's client_id as user_id. The root
observation holds what the user sent and what they got back (after output
redaction); the LangChain/LangGraph runs underneath it (agent loop, LLM
generations, tool calls) come from the Langfuse CallbackHandler.

Tracing is on when LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are set (plus
LANGFUSE_BASE_URL for a self-hosted server) and LANGFUSE_TRACING_ENABLED is not
"false". Every exported span goes through the same secret redaction as the
chat output, so keys that reach a prompt or tool output never leave the
process.

The root observation is started with start_observation() rather than as the
current OTel context, and the handler is pointed at it with trace_context. The
/chat stream is a generator that Starlette advances from a fresh context on
each step, so a context manager held open across yields would not work there.
"""
import json
import os

from dotenv import load_dotenv

# The Langfuse client reads its credentials from the environment on creation.
load_dotenv()

from langfuse import Langfuse, propagate_attributes  # noqa: E402
from langfuse.langchain import CallbackHandler  # noqa: E402
from langfuse.types import MaskOtelSpansResult, OtelSpanPatch  # noqa: E402

from agent.guardrail import redact_secrets  # noqa: E402

ENABLED = (
    bool(os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY"))
    and os.environ.get("LANGFUSE_TRACING_ENABLED", "true").lower() != "false"
)


def _redact(value):
    if isinstance(value, str):
        return redact_secrets(value)
    if isinstance(value, list):
        return [_redact(v) for v in value]
    if isinstance(value, dict):
        return {k: _redact(v) for k, v in value.items()}
    return value


def _redact_attribute(value):
    if isinstance(value, (tuple, list)):
        return type(value)(_redact_attribute(v) for v in value)
    if not isinstance(value, str):
        return value
    # Input, output and metadata attributes are JSON-encoded. Redact inside the
    # decoded value so a replacement can't swallow a closing quote or brace.
    try:
        decoded = json.loads(value)
    except ValueError:
        return redact_secrets(value)
    redacted = _redact(decoded)
    return value if redacted == decoded else json.dumps(redacted, ensure_ascii=False)


def mask_spans(*, params):
    patches = {}
    for identifier, span in params.spans.items():
        changed = {}
        for key, value in span.attributes.items():
            new = _redact_attribute(value)
            if new != value:
                changed[key] = new
        if changed:
            patches[identifier] = OtelSpanPatch(set_attributes=changed)
    return MaskOtelSpansResult(span_patches=patches) if patches else None


langfuse = Langfuse(tracing_enabled=ENABLED, mask_otel_spans=mask_spans)


class Turn:
    """One traced request. Pass turn.config(...) to every LangChain call made
    for the request, then call end() with what the user got back."""

    def __init__(self, name, user_input, *, session_id=None, client_id="", tags=(), metadata=None):
        self.root = None
        self.callbacks = []
        # Read by the CallbackHandler at the root of each LangChain run, so the
        # agent's observations carry the same session, user and tags.
        self.metadata = {"langfuse_trace_name": name, "langfuse_tags": list(tags)}
        if session_id:
            self.metadata["langfuse_session_id"] = session_id
        if client_id:
            self.metadata["langfuse_user_id"] = client_id
        if not ENABLED:
            return

        with propagate_attributes(
            trace_name=name,
            session_id=session_id,
            user_id=client_id or None,
            tags=list(tags),
        ):
            self.root = langfuse.start_observation(
                name=name, as_type="span", input=user_input, metadata=metadata
            )
        self.callbacks = [CallbackHandler(
            trace_context={"trace_id": self.root.trace_id, "parent_span_id": self.root.id}
        )]

    def config(self, run_name, **config):
        """LangChain config for one call under this turn."""
        config["callbacks"] = list(config.get("callbacks", [])) + self.callbacks
        config["metadata"] = {**config.get("metadata", {}), **self.metadata}
        config["run_name"] = run_name
        return config

    def end(self, output=None, *, error=None, metadata=None):
        if self.root is None:
            return
        if error is not None:
            self.root.update(level="ERROR", status_message=f"{type(error).__name__}: {error}", metadata=metadata)
        else:
            self.root.update(output=output, metadata=metadata)
        self.root.end()
        self.root = None


# Default for callers that don't trace (tests, eval scripts calling the agent
# directly): same interface, no Langfuse handler.
class _NoTrace(Turn):
    def __init__(self):
        self.root = None
        self.callbacks = []
        self.metadata = {}


NO_TRACE = _NoTrace()
