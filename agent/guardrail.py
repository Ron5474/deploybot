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
_SECRET_NAME = r"[A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)[A-Z0-9_]*"
_KV = re.compile(rf"(?im)\b({_SECRET_NAME})\s*([:=])\s*`?([^\s`]+)`?")

# Streaming can't hold back a fixed number of characters: JWTs, bearer tokens
# and NAME=value pairs have no maximum length, so any fixed window can be
# outgrown. Instead the stream is only ever cut right after whitespace. Most
# patterns above can't contain whitespace, so a secret never straddles such a
# cut. The two that can (_KV and "Bearer <token>") are covered by _OPEN: it
# matches text that ends partway through one of them, e.g. "API_KEY = " or
# "Bearer ", where the next word decides whether there is a secret. A new
# pattern that can span whitespace needs an entry here too.
_OPEN = re.compile(rf"(?i)(?:\b{_SECRET_NAME}\s*(?:[:=]\s*)?|Bearer\s+)\Z")


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


def _can_split_after(left):
    """True if `left` can be redacted on its own, whatever text follows it:
    redact_secrets(left + more) == redact_secrets(left) + redact_secrets(more).
    `left` must end in whitespace."""
    out = left
    for val in _env_secret_values():
        # `left` ends with the start of a known secret value (one with spaces in it)
        if any(out.endswith(val[:n]) for n in range(1, len(val))):
            return False
        out = out.replace(val, REDACTED)
    return out[-1:].isspace() and not _OPEN.search(out)


class StreamRedactor:
    """Incremental redaction for streamed output. Feed chunks; it emits redacted
    text up to the last whitespace that no secret can span, and holds the rest
    back until more text (or flush()) settles it. Only text that is final gets
    emitted, so the pieces always add up to redact_secrets() of the whole input,
    however it was chunked."""

    def __init__(self):
        self._buf = ""   # raw text not emitted yet
        self._out = ""   # redacted text emitted so far

    def feed(self, chunk):
        if not chunk:
            return ""
        self._buf += chunk
        # Cut at the latest safe whitespace; usually that is the last one.
        for gap in reversed(list(re.finditer(r"\s+", self._buf))):
            if _can_split_after(self._buf[:gap.end()]):
                piece = redact_secrets(self._buf[:gap.end()])
                self._buf = self._buf[gap.end():]
                self._out += piece
                return piece
        return ""

    def flush(self):
        piece = redact_secrets(self._buf)
        self._buf = ""
        self._out += piece
        return piece

    @property
    def full_redacted(self):
        return self._out + redact_secrets(self._buf)
