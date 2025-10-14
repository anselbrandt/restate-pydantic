import asyncio
import json
import re
import os

from dotenv import load_dotenv
from tavily import AsyncTavilyClient

from app.schemas.lead_generator import LinkedInLeadQueries, TavilyResponse, SearchQuery

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

tavily_client = AsyncTavilyClient(api_key=TAVILY_API_KEY)


def clean_query(query: str) -> str:
    cleaned = query.replace('\\"', "").replace('"', "")
    cleaned = re.sub(r"\s*site:linkedin\.com/in/\s*", "", cleaned)
    cleaned = " ".join(cleaned.split())
    if cleaned.strip():
        return f"{cleaned} site:linkedin.com/in/"
    else:
        return "site:linkedin.com/in/"


async def execute_single_search(query: SearchQuery):
    raw_response = await tavily_client.search(
        query=f"{query.query} site:linkedin.com/in/",
        include_raw_content=True,
        max_results=10,
        include_domains=["linkedin.com"],
    )

    tavily_response = TavilyResponse(**raw_response)

    filtered_results = [
        result for result in tavily_response.results if "/in/" in result.url
    ]

    result = {
        "query": query.query,
        "description": query.description,
        "results": [result.model_dump() for result in filtered_results],
        "result_count": len(tavily_response.results),
        "success": True,
    }

    return result


async def main():
    with open("structured_leads.json", "r", encoding="utf-8") as f:
        data = json.loads(f.read())

    leads = LinkedInLeadQueries(**data)

    tiers = leads.priority_tiers
    tier_results_map = {}
    priority_1_results = []
    total_queries_processed = 0

    for tier in tiers:
        tier_results_map[tier.tier_name] = {
            "tier_name": tier.tier_name,
            "tier_description": tier.tier_description,
            "priority_level": tier.priority_level,
            "tier_results": [],
            "total_results": 0,
        }
        print(tier.tier_name)
        for q in tier.queries:
            print(q.query)
            result = await execute_single_search(q)
            total_queries_processed += 1
            tier_results_map[tier.tier_name]["tier_results"].append(result)
            tier_results_map[tier.tier_name]["total_results"] += result.get(
                "result_count", 0
            )

            if tier.priority_level == 1 and result.get("success", False):
                for search_result in result.get("results", []):
                    priority_1_results.append(search_result)
    search_results_organized = list(tier_results_map.values())
    priority_1_results.sort(key=lambda x: x.get("score", 0), reverse=True)

    with open("search_results_organized.json", "w", encoding="utf-8") as f:
        json.dump(search_results_organized, f, indent=2)
    with open("priority_1_results.json", "w", encoding="utf-8") as f:
        json.dump(priority_1_results, f, indent=2)


if __name__ == "__main__":
    asyncio.run(main())
