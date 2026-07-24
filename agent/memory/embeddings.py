import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_client = OpenAI(
    api_key =os.getenv("GEMINI_API_KEY"),
    base_url = "https://generativelanguage.googleapis.com/v1beta/openai/",
)

EMBED_DIMS = 1536

def embed(text):
    response = _client.embeddings.create(
        model = os.getenv("GEMINI_EMBED_MODEL"),
        input = text,
        dimensions = EMBED_DIMS,
    )
    return response.data[0].embedding