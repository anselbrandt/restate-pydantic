import asyncio
import json
import os
import urllib.parse

from dotenv import load_dotenv
from httpx import AsyncClient
from pydantic import BaseModel

load_dotenv()

geo_api_key = os.getenv("GEO_API_KEY")
weather_api_key = os.getenv("WEATHER_API_KEY")


class LatLng(BaseModel):
    lat: float
    lng: float


async def get_lat_lng_mock():
    async with AsyncClient() as client:
        location_description = "Tokyo"
        r = await client.get(
            "https://demo-endpoints.pydantic.workers.dev/latlng",
            params={"location": location_description},
        )
        return LatLng.model_validate_json(r.content)


async def get_lat_lng():
    async with AsyncClient() as client:
        location_description = "Tokyo"
        loc = urllib.parse.quote(location_description)
        params = {"access_token": geo_api_key}
        r = await client.get(
            f"https://api.mapbox.com/geocoding/v5/mapbox.places/{loc}.json",
            params=params,
        )
        r.raise_for_status()
        data = r.json()
        with open("location.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        if features := data["features"]:
            lng, lat = features[0]["center"]
            return LatLng(lat=lat, lng=lng)


async def fetch_temperature():
    async with AsyncClient() as client:
        r = await client.get(
            "https://demo-endpoints.pydantic.workers.dev/number",
            params={"min": 10, "max": 30},
        )
        r.raise_for_status()
        return r.text


async def fetch_description(coords: LatLng):
    async with AsyncClient() as client:
        r = await client.get(
            "https://demo-endpoints.pydantic.workers.dev/weather",
            params={"lat": coords.lat, "lng": coords.lng},
        )
        r.raise_for_status()
        return r.text


async def fetch_weather(coords: LatLng):
    async with AsyncClient() as client:
        params = {
            "apikey": weather_api_key,
            "location": f"{coords.lat},{coords.lng}",
            "units": "metric",
        }
        r = await client.get(
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


async def main():
    coords = await get_lat_lng()
    print(coords)
    temp, desc = await asyncio.gather(fetch_temperature(), fetch_description(coords))

    print(temp, "and", desc)
    weather = await fetch_weather(coords)
    print(weather)


if __name__ == "__main__":
    asyncio.run(main())
