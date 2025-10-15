from typing import List
import json
import os

from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent
from restate import RunOptions
from tavily import AsyncTavilyClient
import logfire
import restate

from app.data.example_prompt import example_prompt
from app.restate import RestateAgent
from app.schemas.lead_generator import (
    LinkedInLeadQueries,
    SearchQuery,
    TavilyResponse,
    TavilyResult,
)
from app.system_prompts.lead_generator import (
    structured_instructions,
    unstructured_instructions,
)

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

logfire.configure(send_to_logfire="if-token-present")
logfire.instrument_pydantic_ai()

lead_generator_service = restate.Service("Lead_Generator_Service")


class Prompt(BaseModel):
    prompt: str = example_prompt


@lead_generator_service.handler()
async def run_lead_generator(ctx: restate.Context, prompt: Prompt) -> str:
    with logfire.span("Generating leads") as span:

        unstructured_leads_agent = Agent(
            "openai:gpt-4.1",
            instructions=unstructured_instructions,
            retries=2,
        )
        unstructured_restate_agent = RestateAgent(
            unstructured_leads_agent, restate_context=ctx
        )

        async def unstructured_agent_call(prompt_text: str) -> str:
            result = await unstructured_restate_agent.run(prompt_text)
            return result.output

        structured_leads_agent = Agent[None, LinkedInLeadQueries](
            "openai:gpt-4.1-mini",
            instructions=structured_instructions,
            output_type=LinkedInLeadQueries,
            retries=3,
        )

        structured_restate_agent: RestateAgent[None, LinkedInLeadQueries] = (
            RestateAgent(structured_leads_agent, restate_context=ctx)
        )

        async def structured_leads_agent_call(prompt_text: str) -> LinkedInLeadQueries:
            result = await structured_restate_agent.run(prompt_text)
            return result.output

        unstructured_output = await ctx.run_typed(
            "Freeform leads generator",
            unstructured_agent_call,
            RunOptions(max_attempts=3),
            prompt_text=prompt.prompt,
        )

        structured_output: LinkedInLeadQueries = await ctx.run_typed(
            "Structured leads generator",
            structured_leads_agent_call,
            RunOptions(max_attempts=3, type_hint=LinkedInLeadQueries),
            prompt_text=f"Structure these LinkedIn search queries for automated lead generation: {unstructured_output}",
        )
        # with open("structured_leads.json", "w", encoding="utf-8") as f:
        #     json.dump(structured_output.model_dump(), f, indent=2)

        # return structured_output.model_dump_json()

        class TopQueries(BaseModel):
            queries: List[SearchQuery]

        def query_selector_call(lead_queries: LinkedInLeadQueries) -> TopQueries:
            """Extract all queries from priority level 1 tiers (compact version)."""
            top_queries = [
                query
                for tier in lead_queries.priority_tiers
                if tier.priority_level == 1
                for query in tier.queries
            ]
            return TopQueries(queries=top_queries)

        top_queries: TopQueries = await ctx.run_typed(
            "Top queries",
            query_selector_call,
            RunOptions(max_attempts=3, type_hint=TopQueries),
            structured_output,
        )

        # with open("top_queries.json", "w", encoding="utf-8") as f:
        #     json.dump(top_queries.model_dump(), f, indent=2)

        # return top_queries.model_dump_json()

        class QueryResults(BaseModel):
            query: str
            description: str
            results: List[TavilyResult]

        async def query_executor_call(top_queries: TopQueries) -> QueryResults | None:
            tavily_client = AsyncTavilyClient(api_key=TAVILY_API_KEY)
            for q in top_queries.queries:
                query = f"{q.query} site:linkedin.com"
                raw_response = await tavily_client.search(
                    query=query,
                    include_raw_content=True,
                    max_results=10,
                    include_domains=["linkedin.com"],
                )
                response = TavilyResponse(**raw_response)
                results = [
                    result.model_dump()
                    for result in response.results
                    if "/in/" in result.url
                ]
                return QueryResults(
                    query=q.query, description=q.description, results=results
                )

        leads: QueryResults = await ctx.run_typed(
            "Query results",
            query_executor_call,
            RunOptions(max_attempts=3, type_hint=QueryResults),
            top_queries,
        )

        with open("leads.json", "w", encoding="utf-8") as f:
            json.dump(leads.model_dump(), f, indent=2)

        return leads.model_dump_json()
