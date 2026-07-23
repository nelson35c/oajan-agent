import os
from dotenv import load_dotenv
from tavily import TavilyClient
from agent.tools import tool

load_dotenv()

_client = TavilyClient(api_key = os.getenv("TAVILY_API_KEY"))

WEB_SEARCH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search teh web for current factual information the model doesnt know. Use fro recent events, or anything that needs up to date data",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"},
            },
            "required": ["query"],
        },
    },
}

@tool(WEB_SEARCH_SCHEMA)
def web_search(query):
    try:
        response = _client.search(query=query, max_results=3)
    except Exception as exc:
        return f"Error searching the web: {exc}"

    results = response.get("results", [])
    if not results:
        return "No results found"

    lines = []
    for r in results:
        lines.append(f"- {r['title']}\n {r['url']}\n {r['content'][:300]}")
    return "\n".join(lines)







