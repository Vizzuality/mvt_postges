"""Main Script"""

import logging

import io
import os
import json

from aiohttp_apispec import (docs,
                             request_schema,
                             response_schema,
                             setup_aiohttp_apispec,
                             validation_middleware)
from marshmallow import Schema, fields
from aiohttp import web
import aiopg.sa
from aiohttp_swagger import setup_swagger

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import inspect
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

import sys
import itertools

## Setting up the logs
formatter = logging.Formatter('%(asctime)s  - %(funcName)s - %(lineno)d - %(name)s - %(levelname)s - %(message)s',
                              '%Y%m%d-%H:%M%p')

logging.basicConfig(
    level='DEBUG',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y%m%d-%H:%M%p',
)

root = logging.getLogger()
root.setLevel(logging.DEBUG)

error_handler = logging.StreamHandler(sys.stderr)
error_handler.setLevel(logging.WARN)
error_handler.setFormatter(formatter)
root.addHandler(error_handler)

output_handler = logging.StreamHandler(sys.stdout)
output_handler.setLevel('DEBUG')
output_handler.setFormatter(formatter)
root.addHandler(output_handler)

#setting up schemas
class RequestSchema(Schema):
    bool_field = fields.Bool()

class RequestTileSchema(Schema):
    query = fields.Str(description='query parameters')
    z = fields.Int(description='Zoom level')
    x = fields.Int(description='x')
    y = fields.Int(description='y')


class ResponseSchema(Schema):
    msg = fields.Str()
    data = fields.List()
###functions to get the Tiles

async def GeneratePrepared():
    prepared = f"""PREPARE gettile(text, numeric, numeric, numeric) AS 
    			  SELECT ST_ASMVT('data', 4096, 'mvtgeometry', tile) 
    			  FROM (select *, ST_AsMVTGeom(geometry,ST_TileEnvelope($2,$3,$4),4096,0,true) AS mvtgeometry from ($1) as data WHERE ST_AsMVTGeom(geometry, ST_TileEnvelope($2,$3,$4),4096,0,true) IS NOT NULL) AS tile;
    		   """

    logging.info(prepared)
    return(prepared)

async def init_pg(app):
	
	conf = app['config']['postgres']
	prepared = await GeneratePrepared()
	engine = await aiopg.sa.create_engine(
	    database='test',
	    user=conf['user'],
	    password=conf['password'],
	    host=conf['host'],
	    port=conf['port'],
	    minsize=conf['minsize'],
	    maxsize=conf['maxsize'],
	)
	inspector = inspect(engine)
	DBSession = sessionmaker(bind=engine)
	session = DBSession()
	session.execute(prepared)
	
	app['db'] = engine

async def close_pg(app):
    app['db'].close()
    await app['db'].wait_closed()
#
#async def setup_redis(app, conf, loop):
#    pool = await init_redis(conf['redis'], loop)
#
#    async def close_redis(app):
#        pool.close()
#        await pool.wait_closed()
#
#    app.on_cleanup.append(close_redis)
#    app['redis_pool'] = pool
#    return pool
##prepare the routes
routes = web.RouteTableDef()

@docs(tags=['tiles endpoint'],
      summary='Test method summary',
      description='Test method description')
@request_schema(RequestTileSchema())
@response_schema(ResponseSchema(), 200)
@routes.get('/tiles/{z:([0-9]+)}/{x:([0-9]+)}/{y:([0-9]+)}.pbf')
async def get_mvt(request):
	headers = {"Content-Type":"application/x-protobuf",
	"Content-Disposition": "attachment",
	"Access-Control-Allow-Origin": "*"
	}
    final_query = f"EXECUTE gettile({request.query['sql']}, {request.match_info['z']}, {request.match_info['x']}, {request.match_info['y']});"
    async with request.app['db'].acquire() as conn:
    	records = await conn.execute(final_query).fetchall()
        response = [dict(q) for q in records]
    content = io.BytesIO(response).getvalue()

    return web.response(body= content, headers=headers)

@docs(tags=['query endpoint'],
      summary='Test method summary',
      description='Test method description')
@request_schema(RequestSchema())
@response_schema(ResponseSchema(), 200)                              
@routes.get('/v1/query', name='test')
async def hello_world(request):
	logging.info(request.match_info)
	logging.info(request.app)
	final_query = f"EXECUTE {request.query['sql']}"
	async with request.app['db'].acquire() as conn:
    	records = await conn.execute(final_query).fetchall()
    	logging.info(records)
        response = [io.BytesIO(q).getvalue() for q in records] 
	
	return web.json_response({'msg': 'done', 'data': response})



async def init(loop):
	

    app = web.Application(loop=loop)
    app['config'] = os.environ
    app.on_startup.append(init_pg)
    app.on_cleanup.append(close_pg)
    app.add_routes(routes)
    app.middlewares.append(validation_middleware)
    setup_aiohttp_apispec(app=app,
                      request_data_name='validated_data',
                      title='My Documentation',
                      version='v1',
                      url='/v1/api/docs/api-docs')
    async def swagger(app):
        setup_swagger(
            app=app, swagger_url='/v1/api/docs', swagger_info=app['swagger_dict']
        )
    app.on_startup.append(swagger)

    return app