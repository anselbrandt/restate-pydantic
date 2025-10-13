import asyncio

from dotenv import load_dotenv
import hypercorn
import restate

from app.chaining import call_chaining_svc
from app.weather import weather_service
from app.weather_advanced import weather_service_advanced

load_dotenv()

app = restate.app(
    services=[call_chaining_svc, weather_service, weather_service_advanced]
)

if __name__ == "__main__":
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(hypercorn.asyncio.serve(app, conf))
