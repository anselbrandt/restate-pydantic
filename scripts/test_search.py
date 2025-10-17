import json
import os

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
response = tavily_client.search("Who is Leo Messi?")
with open("search_results.json", "w", encoding="utf-8") as f:
    json.dump(response, f, indent=2)

print("search results saved to search_results.json")
