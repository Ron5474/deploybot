import random

import pytest

from agent.guardrail import StreamRedactor, redact_secrets

JWT = "eyJ" + "x" * 120 + "." + "y" * 40 + "." + "z" * 40
BEARER = "Bearer " + "a1B2c3D4" * 15
SK_KEY = "sk-proj-" + "Ab3dEf6h" * 8
GH_TOKEN = "ghp_" + "a1B2c3D4e5" * 4

# (input, expected redacted output). Each secret is longer than the old fixed
# 96-character holdback or sits where a chunk boundary can split it.
CASES = [
    (f"use this one {JWT} then restart", "use this one [REDACTED] then restart"),
    (f"Authorization: {BEARER} and retry", "Authorization: [REDACTED] and retry"),
    (f"the key is {SK_KEY} keep it safe", "the key is [REDACTED] keep it safe"),
    (f"push with {GH_TOKEN} as the password", "push with [REDACTED] as the password"),
    ("set SOME_API_KEY=abc123def456 in .env", "set SOME_API_KEY= [REDACTED] in .env"),
]
CASE_IDS = ["jwt", "bearer", "sk-key", "github-token", "name-value"]

# Extra shapes for the chunking property test: spaces and newlines inside a
# NAME = value pair, backticks, secret-ish words in ordinary prose, secrets at
# the very start and end, and text with no whitespace at all.
PROPERTY_INPUTS = [text for text, _ in CASES] + [
    "",
    "plain text with no secrets, just words and a trailing space ",
    "The token is stored in the vault and the key point is to rotate it.",
    "DB_PASSWORD = hunter2 and API_TOKEN : `tok_12345` are both set",
    "password:\n\nhunter2\nnext line",
    f"{SK_KEY}",
    f"{JWT}",
    f"first {GH_TOKEN}, then {SK_KEY}; finally {BEARER}",
    f"Bearer\n  {'tok' * 20}== trailing",
    "Bearer short and KEY= ``SECRET : value",
    f"task-{'a' * 30} xoxb-{'1' * 12}-{'b' * 12} done",
    "no_whitespace_here_at_all",
    "ends with a secret name API_KEY",
    "ends mid pair API_KEY = ",
]


def stream(text, size):
    """Feed `text` to a StreamRedactor in chunks of `size` and return the pieces."""
    r = StreamRedactor()
    pieces = [r.feed(text[i:i + size]) for i in range(0, len(text), size)]
    pieces.append(r.flush())
    return pieces


@pytest.mark.parametrize("text,expected", CASES, ids=CASE_IDS)
def test_batch_redaction(text, expected):
    assert redact_secrets(text) == expected


@pytest.mark.parametrize("text,expected", CASES, ids=CASE_IDS)
def test_streamed_in_small_chunks_matches_batch(text, expected):
    assert "".join(stream(text, 5)) == expected


@pytest.mark.parametrize("text,expected", CASES, ids=CASE_IDS)
def test_no_piece_of_the_stream_contains_secret_material(text, expected):
    # Checks every emitted piece, not just the joined result: a prefix that
    # leaks in an early chunk has already reached the client.
    secrets = [JWT, BEARER.split()[1], SK_KEY, GH_TOKEN, "abc123def456"]
    emitted = ""
    for piece in stream(text, 5):
        emitted += piece
        for secret in secrets:
            assert secret[:12] not in emitted


@pytest.mark.parametrize("text", PROPERTY_INPUTS, ids=range(len(PROPERTY_INPUTS)))
def test_any_chunk_size_matches_batch(text):
    expected = redact_secrets(text)
    for size in range(1, 51):
        assert "".join(stream(text, size)) == expected, f"chunk size {size}"


@pytest.mark.parametrize("text", PROPERTY_INPUTS, ids=range(len(PROPERTY_INPUTS)))
def test_random_chunking_matches_batch(text):
    expected = redact_secrets(text)
    rng = random.Random(0)
    for _ in range(50):
        r = StreamRedactor()
        out, i = "", 0
        while i < len(text):
            step = rng.randint(1, 12)
            out += r.feed(text[i:i + step])
            i += step
        out += r.flush()
        assert out == expected


def test_text_after_a_secret_is_preserved():
    text = f"before {JWT} after one. after two.\nafter three"
    assert "".join(stream(text, 7)) == "before [REDACTED] after one. after two.\nafter three"


def test_text_without_secrets_passes_through_unchanged():
    text = "Run docker compose up -d, then open http://localhost:8080 to finish setup.\n"
    assert redact_secrets(text) == text
    assert "".join(stream(text, 4)) == text


def test_ordinary_text_is_emitted_before_flush():
    r = StreamRedactor()
    # Everything up to the last complete word is released straight away; only
    # the unfinished word "wor" waits for more input.
    assert r.feed("hello there wor") == "hello there "
    assert r.feed("ld ") == "world "
    assert r.flush() == ""


def test_full_redacted_matches_what_was_streamed():
    text = f"token {GH_TOKEN} was rotated"
    r = StreamRedactor()
    out = "".join(r.feed(text[i:i + 3]) for i in range(0, len(text), 3)) + r.flush()
    assert r.full_redacted == out == "token [REDACTED] was rotated"


def test_env_secret_value_is_redacted(monkeypatch):
    monkeypatch.setenv("DEPLOY_SERVICE_TOKEN", "hunter2-plain-looking-value")
    text = "the value is hunter2-plain-looking-value, do not share it"
    assert redact_secrets(text) == "the value is [REDACTED], do not share it"
    assert "".join(stream(text, 5)) == "the value is [REDACTED], do not share it"


def test_env_secret_containing_spaces_is_redacted_when_streamed(monkeypatch):
    monkeypatch.setenv("VAULT_PASSWORD", "correct horse battery staple")
    text = "it is correct horse battery staple, obviously. correct horse only."
    expected = "it is [REDACTED], obviously. correct horse only."
    assert redact_secrets(text) == expected
    for size in range(1, 51):
        assert "".join(stream(text, size)) == expected, f"chunk size {size}"


def test_env_var_without_secret_name_is_not_redacted(monkeypatch):
    monkeypatch.setenv("DEPLOY_REGION", "us-west-2-primary")
    text = "deployed to us-west-2-primary today"
    assert redact_secrets(text) == text
