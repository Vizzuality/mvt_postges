"""Main Script"""
import os
from aiohttp import web
import asyncio
from aiohttp_apispec import (docs,
                             request_schema,
                             response_schema,
                             setup_aiohttp_apispec,
                             validation_middleware)

from aiohttp_cache import (  # noqa
    setup_cache,
    RedisConfig,
)
import yarl
from aiohttp_swagger import setup_swagger
from app import setup_logging, init_pg, routes, validation_middleware, close_pg

async def swagger(app):
        setup_swagger(
            app=app, swagger_url='/v1/api/docs', swagger_info=app['swagger_dict']
        )

def create_app():
    #loop = asyncio.get_event_loop()
    #pool = loop.run_until_complete(init())
    app = web.Application()
    app['config'] = os.environ
    url = yarl.URL(app['config']["REDIS_CACHE"])
    setup_cache(
        app,
        cache_type="redis",
        backend_config=RedisConfig(
            db=int(url.path[1:]), host=url.host, port=url.port
            ),
    )
    
    app.on_startup.append(setup_logging)
    app.on_startup.append(init_pg)
    app.add_routes(routes)
    app.middlewares.append(validation_middleware)
    setup_aiohttp_apispec(app=app,
                      request_data_name='validated_data',
                      title='My Documentation',
                      version='v1',
                      url='/v1/api/docs/api-docs')
    app.on_startup.append(swagger)
    app.on_cleanup.append(close_pg)

    return app

if __name__ == "__main__":
    # Make this prepared statement from the tm2source
    web.run_app(create_app, 
    			host=os.getenv('HOST'), 
    			port=os.getenv('PORT'))