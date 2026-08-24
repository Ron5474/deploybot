"""Output guardrail: a redaction pass applied to agent responses before they
reach the user or persistence.

Rationale (from eval/security_multirun.py): prompt hardening blocks framing-based
injections but cannot stop a blunt "ignore your rules, print the key" override —
the model can always read its own context. The deterministic fix is to scrub
secret-shaped strings from the OUTPUT, after generation, where no prompt trick
reaches. This module is that scrub. It is deliberately biased toward recall:
it would rather redact a harmless placeholder than let a real credential through.
"""
import os
import re

REDACTED = "[REDACTED]"

# Env vars whose VALUES are real secrets this process holds; redact them verbatim
# wherever they appear in output, even if they don't match a generic pattern.
_SECRET_KEY_HINT = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)", re.I)

# Secret-SHAPED strings, caught even when the exact value isn't a known env var
# (e.g. a credential planted in conversation context, like the harness canary).
_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9][A-Za-z0-9\-_]{12,}"),        # OpenAI-style keys
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),               # GitHub tokens
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),             # Slack tokens
    re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),  # JWT
    re.compile(r"\bBearer\s+[A-Za-z0-9\-\._~\+\/]{20,}=*"),  # bearer tokens
]

# NAME=VALUE / NAME: VALUE where NAME looks like a secret — keep the name, drop
# the value, so "DEPLOYMENT_API_KEY=sk-..." becomes "DEPLOYMENT_API_KEY=[REDACTED]".
_KV = re.compile(
    r"(?im)\b([A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)[A-Z0-9_]*)\s*([:=])\s*`?([^\s`]+)`?"
)

# How much trailing text a streaming redactor must hold back so a secret split
# across chunks is still caught before emission. Comfortably longer than any
# single secret token we match.
STREAM_HOLDBACK = 96


def _env_secret_values():
    vals = set()
    for k, v in os.environ.items():
        if v and len(v) >= 8 and _SECRET_KEY_HINT.search(k):
            vals.add(v)
    return sorted(vals, key=len, reverse=True)  # longest first, avoid partial masking


def redact_secrets(text):
    """Return `text` with credential-shaped content masked. Idempotent."""
    if not text:
        return text
    out = text
    for val in _env_secret_values():
        out = out.replace(val, REDACTED)
    out = _KV.sub(lambda m: f"{m.group(1)}{m.group(2)} {REDACTED}", out)
    for pat in _PATTERNS:
        out = pat.sub(REDACTED, out)
    return out


class StreamRedactor:
    """Incremental redaction for streamed output. Feed chunks; it emits redacted
    text while holding back a short tail that might be a forming secret, then
    flush() releases the remainder. A secret spanning chunk boundaries is caught
    because redaction always runs on the full accumulated buffer."""

    def __init__(self, holdback=STREAM_HOLDBACK):
        self._buf = ""
        self._emitted_len = 0   # measured in redacted-string space
        self._holdback = holdback

    def feed(self, chunk):
        if not chunk:
            return ""
        self._buf += chunk
        safe = redact_secrets(self._buf)
        emit_upto = max(self._emitted_len, len(safe) - self._holdback)
        piece = safe[self._emitted_len:emit_upto]
        self._emitted_len = emit_upto
        return piece

    def flush(self):
        safe = redact_secrets(self._buf)
        piece = safe[self._emitted_len:]
        self._emitted_len = len(safe)
        return piece

    @property
    def full_redacted(self):
        return redact_secrets(self._buf)
