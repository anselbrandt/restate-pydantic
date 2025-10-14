import asyncio
from hypercorn.asyncio import serve
from dotenv import load_dotenv
import hypercorn
import restate

from app.chaining import call_chaining_svc
from app.chaining_typed import call_chaining_svc_typed
from app.search import search_service
from app.weather import weather_service
from app.weather_advanced import weather_service_advanced


load_dotenv()

app = restate.app(
    services=[
        call_chaining_svc_typed,
        call_chaining_svc,
        search_service,
        weather_service_advanced,
        weather_service,
    ]
)

if __name__ == "__main__":
    conf = hypercorn.Config()
    conf.bind = ["0.0.0.0:9080"]
    asyncio.run(serve(app, conf))
