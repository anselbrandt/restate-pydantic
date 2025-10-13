import asyncio
from dataclasses import dataclass
from typing import Any


from dotenv import load_dotenv
from httpx import AsyncClient
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from restate import Context
import logfire
import restate

from app.restate import RestateAgent


load_dotenv()

logfire.configure(send_to_logfire="if-token-present")
logfire.instrument_pydantic_ai()


@dataclass
class Deps:
    client: AsyncClient
    restate_context: Context


weather_agent = Agent[Deps](
    "openai:gpt-4.1-mini",
    # 'Be concise, reply with one sentence.' is enough for some models (like openai) to use
    # the below tools appropriately, but others like anthropic and gemini require a bit more direction.
    instructions="Be concise, reply with one sentence.",
    deps_type=Deps,
)


class LatLng(BaseModel):
    lat: float
    lng: float


@weather_agent.tool
async def get_lat_lng(ctx: RunContext[Deps], location_description: str) -> LatLng:
    """Get the latitude and longitude of a location.

    Args:
        ctx: The context.
        location_description: A description of a location.
    """

    async def action():
        # NOTE: the response here will be random, and is not related to the location description.
        r = await ctx.deps.client.get(
            "https://demo-endpoints.pydantic.workers.dev/latlng",
            params={"location": location_description},
        )
        r.raise_for_status()
        return LatLng.model_validate_json(r.content)

    return await ctx.deps.restate_context.run_typed("Getting lat/lng", action)


@weather_agent.tool
async def get_weather(ctx: RunContext[Deps], lat: float, lng: float) -> dict[str, Any]:
    """Get the weather at a location.

    Args:
        ctx: The context.
        lat: Latitude of the location.
        lng: Longitude of the location.
    """

    async def fetch_temperature():
        r = await ctx.deps.client.get(
            "https://demo-endpoints.pydantic.workers.dev/number",
            params={"min": 10, "max": 30},
        )
        r.raise_for_status()
        return r.text

    async def fetch_description():
        r = await ctx.deps.client.get(
            "https://demo-endpoints.pydantic.workers.dev/weather",
            params={"lat": lat, "lng": lng},
        )
        r.raise_for_status()
        return r.text

    temp_response_fut = ctx.deps.restate_context.run_typed(
        "Fetching temperature", fetch_temperature
    )
    descr_response_fut = ctx.deps.restate_context.run_typed(
        "Fetching description", fetch_description
    )

    await asyncio.gather(temp_response_fut, descr_response_fut)

    return {
        "temperature": f"{await temp_response_fut} °C",
        "description": await descr_response_fut,
    }


weather_service_advanced = restate.Service(name="weather_advanced")


@weather_service_advanced.handler()
async def handle_weather_request(ctx: Context, city: str):
    async with AsyncClient() as client:
        restate_agent = RestateAgent(weather_agent, restate_context=ctx)
        deps = Deps(client=client, restate_context=ctx)
        result = await restate_agent.run(
            f"What is the weather like in {city}?", deps=deps
        )
        return result.output
