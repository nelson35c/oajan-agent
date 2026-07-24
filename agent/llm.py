import os
from dotenv import load_dotenv
from openai import OpenAI, BadRequestError
from agent import trace

load_dotenv()

MODEL = os.getenv("GROQ_CHAT_MODEL")

client = OpenAI(
    api_key = os.getenv("GROQ_API_KEY"),
    base_url = "https://api.groq.com/openai/v1"
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

 