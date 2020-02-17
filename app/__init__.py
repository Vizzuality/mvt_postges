"""Main Script"""

import logging

import io
import os
import json
import datetime as dt

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

class JSONDateEncoder(json.JSONEncoder):
	"""
	A subclass of JSONEncoder that can convert datetime and date objects to an
	RFC3339-compliant string format. The resulting format is always:
	   `YYYY-MM-DDTHH:MM:SS.SSSSSSZ`
	"""

	def default(self, obj):
		if isinstance(obj, dt.datetime):
			return obj.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
		elif isinstance(obj, dt.date):
			return obj.isoformat()
		else:
			return super().default(obj)

## Setting up the logs
async def setup_logging(app):
	formatter = logging.Formatter('%(asctime)s  - %(funcName)s - %(lineno)d - %(name)s - %(levelname)s - %(message)s',
								'%Y%m%d-%H:%M%p')

	logging.basicConfig(
		level='DEBUG',
		format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
		datefmt='%Y%m%d-%H:%M%p',
	)

	#root = logging.getLogger()
	#root.setLevel(logging.DEBUG)

	#error_handler = logging.StreamHandler(sys.stderr)
	#error_handler.setLevel(logging.WARN)
	#error_handler.setFormatter(formatter)
	#root.addHandler(error_handler)

	#output_handler = logging.StreamHandler(sys.stdout)
	#output_handler.setLevel('DEBUG')
	#output_handler.setFormatter(formatter)
	#root.addHandler(output_handler)



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
	data = fields.List(fields.Dict())

async def GeneratePrepared():
	prepared = f"""PREPARE gettile(text, int, int, int) AS  
				  SELECT ST_ASMVT(tile.*, 'layer0', 4096, 'mvtgeometry', 'feature_id')
				  FROM (SELECT *, ST_AsMVTGeom(the_geom, ST_TileEnvelope($2,$3,$4), 4096, 0, true) AS mvtgeometry, ROW_NUMBER() OVER() as feature_id
				  		  FROM (select * from fmus) as data 
						  WHERE ST_AsMVTGeom(the_geom, ST_TileEnvelope($2,$3,$4),4096,0,true) IS NOT NULL) AS tile;
			   """

	logging.info(prepared)
	return(prepared)

async def Query(app, query, asJson = True):
	logging.debug(f"{query}")
	async with app['db'].acquire() as conn:
		fetchQuery = await conn.execute(query)
		results = await fetchQuery.fetchall()
		#
		response = [{column: value for column, value in rowproxy.items()} for rowproxy in results]
	if not asJson:
		response = [dict(q) for q in results]
		logging.debug(f"{response}")
		response = io.BytesIO(response[0]['tile']).getvalue()
		
	logging.debug(f"{response}")
	return response

async def init_pg(app):
	
	conf = app['config']
	engine = await aiopg.sa.create_engine(
		database=conf['database'],
		user=conf['user'],
		password=conf['password'],
		host=conf['psqlHost'],
		port=conf['psqlPort'],
		minsize=1,
		maxsize=5)

	#prepared = await GeneratePrepared()
	
	app['db'] = engine
	#await Query(app, prepared)



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
##functions to get the Tiles


routes = web.RouteTableDef()

@docs(tags=['tiles endpoint'],
	  summary='Test method summary',
	  description='Test method description')
@request_schema(RequestTileSchema())
#@response_schema(ResponseSchema(), 200)
@routes.get('/v1/tiles/{z:([0-9]+)}/{x:([0-9]+)}/{y:([0-9]+)}.pbf')
async def get_mvt(request):
	headers = {"Content-Type":"application/x-protobuf",
	"Content-Disposition": "attachment",
	"Access-Control-Allow-Origin": "*"
	}
	#final_query = f"EXECUTE gettile({request.query['sql']}, {request.match_info['z']}, {request.match_info['x']}, {request.match_info['y']});"
	final_query = f"""SELECT ST_ASMVT(tile.*, 'layer0', 4096, 'mvtgeometry', 'id') as tile
				  FROM (SELECT *, ST_AsMVTGeom(the_geom_webmercator, ST_TileEnvelope({request.match_info['z']},{request.match_info['x']},{request.match_info['y']}), 4096, 256, true) AS mvtgeometry
				  		  FROM (select *, st_transform(the_geom, 3857) as the_geom_webmercator from fmus) as data 
						WHERE ST_AsMVTGeom(the_geom_webmercator, ST_TileEnvelope({request.match_info['z']},{request.match_info['x']},{request.match_info['y']}),4096,0,true) IS NOT NULL) AS tile;
					"""
	logging.info(f"[Tile query]: {final_query}")
	
	content =await Query(request.app, final_query, asJson = False)

	return web.Response(body= content, headers=headers)

@docs(tags=['query endpoint'],
	  summary='Allow queries to the selected database',
	  description='Test method description')
@request_schema(RequestSchema())
@response_schema(ResponseSchema(), 200)                              
@routes.get('/v1/query', name='test')
async def hello_world(request):
	try:
		final_query = f"{request.query['sql']}"
		output = await Query(request.app, final_query)
		logging.debug(f"[query:output]: {output}") 
		
		return web.Response(text=json.dumps(output, cls=JSONDateEncoder),
									content_type='application/json',
									status=200)
	except Exception as e:
		logging.error(e)
		raise web.HTTPInternalServerError(text="error")




async def init(loop):
	
	
	app = web.Application(loop=loop)
	app['config'] = os.environ
	app.on_startup.append(setup_logging)
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