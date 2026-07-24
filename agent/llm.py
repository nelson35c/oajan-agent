import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

MODEL = os.getenv("GROQ_CHAT_MODEL")

client = OpenAI(
    api_key = os.getenv("GROQ_API_KEY"),
    base_url = "https://api.groq.com/openai/v1"
)

def complete(messages, tools=None):
    response = client.chat.completions.create(
        model = MODEL,
        messages = messages,
        tools = tools,
    )
    return response.choices[0].message

 