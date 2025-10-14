from dataclasses import dataclass
from typing import Any
import os
import urllib.parse


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
    weather_api_key: str | None
    geo_api_key: str | None


weather_agent = Agent[Deps](
    "openai:gpt-4.1-mini",
    # 'Be concise, reply with one sentence.' is enough for some models (like openai) to use
    # the below tools appropriately, but others like anthropic and gemini require a bit more direction.
    instructions="Be concise, reply with one sentence.",
    deps_type=Deps,
)


@weather_agent.tool
async def get_lat_lng(ctx: RunContext[Deps], location_description: str) -> dict:
    """Get the latitude and longitude of a location.

    Args:
        ctx: The context.
        location_description: A description of a location.
    """
    params = {"access_token": ctx.deps.geo_api_key}
    loc = urllib.parse.quote(location_description)

    async def action():
        r = await ctx.deps.client.get(
            f"https://api.mapbox.com/geocoding/v5/mapbox.places/{loc}.json",
            params=params,
        )
        r.raise_for_status()
        data = r.json()
        if features := data["features"]:
            lng, lat = features[0]["center"]
            return {lat: lat, lng: lng}

    return await ctx.deps.restate_context.run_typed("Getting lat/lng", action)


@weather_agent.tool
async def get_weather(ctx: RunContext[Deps], lat: float, lng: float) -> dict[str, Any]:
    """Get the weather at a location.

    Args:
        ctx: The context.
        lat: Latitude of the location.
        lng: Longitude of the location.
    """
    params = {
        "apikey": ctx.deps.weather_api_key,
        "location": f"{lat},{lng}",
        "units": "metric",
    }

    async def fetch_weather():
        r = await ctx.deps.client.get(
            "https://api.tomorrow.io/v4/weather/realtime", params=params
        )
        r.raise_for_status()
        data = r.json()
        values = data["data"]["values"]
        # https://docs.tomorrow.io/reference/data-layers-weather-codes
        code_lookup = {
            1000: "Clear, Sunny",
            1100: "Mostly Clear",
            1101: "Partly Cloudy",
            1102: "Mostly Cloudy",
            1001: "Cloudy",
            2000: "Fog",
            2100: "Light Fog",
            4000: "Drizzle",
            4001: "Rain",
            4200: "Light Rain",
            4201: "Heavy Rain",
            5000: "Snow",
            5001: "Flurries",
            5100: "Light Snow",
            5101: "Heavy Snow",
            6000: "Freezing Drizzle",
            6001: "Freezing Rain",
            6200: "Light Freezing Rain",
            6201: "Heavy Freezing Rain",
            7000: "Ice Pellets",
            7101: "Heavy Ice Pellets",
            7102: "Light Ice Pellets",
            8000: "Thunderstorm",
        }
        return {
            "temperature": f'{values["temperatureApparent"]}°C',
            "description": code_lookup.get(values["weatherCode"], "Unknown"),
        }

    weather_response_fut = ctx.deps.restate_context.run_typed(
        "Fetching weather", fetch_weather
    )

    return await weather_response_fut


weather_service_advanced = restate.Service(name="weather_advanced")

example_city_or_cities = "Tokyo and Los Angeles"


class Prompt(BaseModel):
    city_or_cities: str = example_city_or_cities


@weather_service_advanced.handler()
async def handle_weather_request(ctx: Context, prompt: Prompt):
    async with AsyncClient() as client:
        geo_api_key = os.getenv("GEO_API_KEY")
        weather_api_key = os.getenv("WEATHER_API_KEY")
        restate_agent = RestateAgent(weather_agent, restate_context=ctx)
        deps = Deps(
            client=client,
            restate_context=ctx,
            weather_api_key=weather_api_key,
            geo_api_key=geo_api_key,
        )
        result = await restate_agent.run(
            f"What is the weather like in {prompt.city_or_cities}?", deps=deps
        )
        return result.output
