from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional, List
import os


from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from restate import Context, RunOptions
from tavily import AsyncTavilyClient
import logfire
import restate

from app.restate import RestateAgent


load_dotenv()

logfire.configure(send_to_logfire="if-token-present")
logfire.instrument_pydantic_ai()


@dataclass
class Deps:
    client: AsyncTavilyClient
    restate_context: Context
    tavily_api_key: str | None
    todays_date: str


search_agent = Agent[Deps](
    "openai:gpt-4.1-mini",
    instructions="If giving search results to the user, include links when possible.",
    deps_type=Deps,
)


class TavilyResult(BaseModel):
    url: str = Field(description="URL of the search result")
    title: str = Field(description="Title of the search result")
    content: str = Field(description="Content snippet from the search result")
    score: float = Field(description="Relevance score of the result")
    raw_content: Optional[str] = Field(
        default=None, description="Raw content if available"
    )


class TavilyResponse(BaseModel):
    query: str = Field(description="The search query that was executed")
    results: List[TavilyResult] = Field(description="List of search results")
    response_time: float = Field(description="Time taken to execute the search")
    request_id: str = Field(description="Unique identifier for this search request")


@search_agent.tool
async def get_todays_date(ctx: RunContext[Deps]) -> str:
    """Returns today's date"""

    async def fetch_todays_date():
        with logfire.span(
            "getting today's date", todays_date=ctx.deps.todays_date
        ) as span:
            return ctx.deps.todays_date

    return await ctx.deps.restate_context.run_typed(
        "Getting todays date", fetch_todays_date, RunOptions(type_hint=str)
    )


@search_agent.tool
async def tavily_search(ctx: RunContext[Deps], query: str) -> dict:
    """Tavily web search API

    Args:
        query: Search query terms
    """

    async def fetch_search_results():
        with logfire.span("calling Tavily API", query=query) as span:
            response = await ctx.deps.client.search(
                query=query,
                include_raw_content=True,
                max_results=10,
            )
            return TavilyResponse(**response)

    return await ctx.deps.restate_context.run_typed(
        "Getting search results",
        fetch_search_results,
        RunOptions(type_hint=TavilyResponse),
    )


search_service = restate.Service(name="search_service")

example_prompt = "Give me the box scores for all Major League baseball games yesterday and give me links to each game."


class Prompt(BaseModel):
    prompt: str = example_prompt


@search_service.handler()
async def handle_search_request(ctx: Context, prompt: Prompt):
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    tavily_client = AsyncTavilyClient(api_key=tavily_api_key)
    current_date = date.today()
    date_string = current_date.strftime("%Y-%m-%d")
    deps = Deps(
        client=tavily_client,
        restate_context=ctx,
        tavily_api_key=tavily_api_key,
        todays_date=date_string,
    )
    restate_agent = RestateAgent(search_agent, restate_context=ctx)
    result = await restate_agent.run(prompt.prompt, deps=deps)
    print(result.output)
    return result.output
