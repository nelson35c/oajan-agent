import os
from dotenv import load_dotenv
from openai import BadRequestError
from agent import trace

load_dotenv()

MODEL = os.getenv("ANTHROPIC_CHAT_MODEL")

# When LangFuse is configured, use its drop-in OpenAI client so every call is
# captured as a generation (model, tokens, cost, latency) under the active
# turn trace. Otherwise fall back to the plain client — same interface.
if trace.langfuse_enabled():
    from langfuse.openai import OpenAI
else:
    from openai import OpenAI

client = OpenAI(
    api_key = os.getenv("ANTHROPIC_API_KEY"),
    base_url = "https://api.anthropic.com/v1/"
)

def complete(messages, tools=None, retries=1):
    for attempt in range(retries + 1):
        try:
            response = client.chat.completions.create(
                model = MODEL,
                messages = messages,
                tools = tools,
            )
            return response.choices[0].message
        except BadRequestError as exc:
            if "tool_use_failed" in str(exc) and attempt < retries:
                trace.retry(attempt + 1, exc)
                continue
            raise

 