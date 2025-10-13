from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from restate import Service, Context
import logfire

from app.restate import RestateAgent


load_dotenv()

logfire.configure(send_to_logfire="if-token-present")
logfire.instrument_pydantic_ai()

weather_agent = Agent(
    "openai:gpt-4.1-mini",
    # 'Be concise, reply with one sentence.' is enough for some models (like openai) to use
    # the below tools appropriately, but others like anthropic and gemini require a bit more direction.
    instructions="Be concise, reply with one sentence.",
)


class LatLng(BaseModel):
    lat: float
    lng: float


@weather_agent.tool
async def get_lat_lng(ctx: RunContext[None], location_description: str) -> LatLng:
    """Get the latitude and longitude of a location.

    Args:
        ctx: The context.
        location_description: A description of a location.
    """
    return LatLng(lat=10.0, lng=20.0)


@weather_agent.tool
async def get_weather(ctx: RunContext[None], lat: float, lng: float) -> dict[str, Any]:
    """Get the weather at a location.

    Args:
        ctx: The context.
        lat: Latitude of the location.
        lng: Longitude of the location.
    """

    return {
        "temperature": "20 °C",
        "description": "Sunny",
    }


weather_service = Service(name="weather")

example_city = "Tokyo"


class Prompt(BaseModel):
    city: str = example_city


@weather_service.handler()
async def handle_weather_request(ctx: Context, prompt: Prompt) -> str:
    restate_agent = RestateAgent(weather_agent, restate_context=ctx)
    result = await restate_agent.run(f"What is the weather like in {prompt.city}?")
    return result.output
