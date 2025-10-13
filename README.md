# Restate / Pydantic AI

### Based on [[WIP]: Add Restate Durable Execution#2998](https://github.com/pydantic/pydantic-ai/pull/2998/commits)

### API Keys

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

### Docker Compose

```bash
docker compose up --build
```

## Manually container orchestration

```bash
docker build -t restate-pydantic .

docker run -p 9080:9080 --env-file .env restate-pydantic
```

### Start Restate Server

```bash
docker run --name restate_dev --rm \
-p 8080:8080 -p 9070:9070 -p 9071:9071 \
--add-host=host.docker.internal:host-gateway \
docker.restate.dev/restatedev/restate:latest
```

### Register Services

```bash
docker run -it --network=host \
docker.restate.dev/restatedev/restate-cli:latest \
deployments register host.docker.internal:9080 --yes
```
