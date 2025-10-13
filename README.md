# Restate / Pydantic AI

### Based on [[WIP]: Add Restate Durable Execution#2998](https://github.com/pydantic/pydantic-ai/pull/2998/commits)

## Running the examples

Create a `.env` file in the root folder with your OpenAI API key as an environment variable:

```
OPENAI_API_KEY=
WEATHER_API_KEY=
GEO_API_KEY=
TAVILY_API_KEY=

```

[OpenAI API key](https://platform.openai.com/api-keys)

[Tomorrow.io Weather API](https://www.tomorrow.io/weather-api/)

[Mapbox Geocoding API](https://docs.mapbox.com/api/search/geocoding/)

[Tavily Search](https://www.tavily.com/)

### Install

```bash
uv sync
```

### Docker

```bash
docker compose up --build
```
