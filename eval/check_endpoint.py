"""Endpoint diagnostic: lists served models, then pings each configured model
with a short timeout. Prints no secrets."""
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
base = os.environ["MODEL_BASE_URL"]
print(f"endpoint: {base}\n")

client = OpenAI(base_url=base, api_key=os.environ["MODEL_API_KEY"], timeout=15.0, max_retries=0)

print("-- models served --")
try:
    for m in client.models.list().data:
        print(f"   {m.id}")
except Exception as e:
    print(f"   FAILED: {type(e).__name__}: {str(e)[:200]}")

print("\n-- ping each configured model (15s timeout, no retries) --")
for var in ("MODEL_NAME", "SMALL_MODEL_NAME"):
    name = os.environ.get(var, "<unset>")
    key = os.environ["MODEL_API_KEY"] if var == "MODEL_NAME" else os.environ["SMALL_MODEL_API_KEY"]
    c = OpenAI(base_url=base, api_key=key, timeout=15.0, max_retries=0)
    try:
        r = c.chat.completions.create(
            model=name,
            messages=[{"role": "user", "content": "Reply with the single word: OK"}],
            max_tokens=10,
        )
        print(f"   {var}={name}: OK -> {(r.choices[0].message.content or '').strip()[:40]}")
    except Exception as e:
        print(f"   {var}={name}: FAILED -> {type(e).__name__}: {str(e)[:200]}")
