"""Main Script"""

import logging

import io
import os
import uuid
import json
import datetime as dt
import sys
import itertools
from decimal import Decimal


from marshmallow import Schema, fields
from aiohttp_apispec import (docs,
                             request_schema,
                             response_schema,
                             setup_aiohttp_apispec,
                             validation_middleware)
from aiohttp_cache import cache
import aiopg.sa
from aiohttp import web

import sqlalchemy



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
        elif isinstance(obj, memoryview):
            return str(obj.tobytes())
        elif isinstance(obj, Decimal):
            return float(obj)
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
    sql = fields.Str(description='query parameters')

class RequestTileSchema(Schema):
    sql = fields.Str(description='query parameters')
    z = fields.Int(description='Zoom level')
    x = fields.Int(description='x')
    y = fields.Int(description='y')

class ResponseSchema(Schema):
    msg = fields.Str()
    data = fields.List(fields.Dict())

async def GeneratePrepared(query, query_id):
    prepared = f"""PREPARE gettile_{query_id}(int, int, int) AS  
                  SELECT ST_ASMVT(tile.*, 'layer0', 4096, 'mvtgeometry', 'ogc_fid') as tile
                  FROM (SELECT *, ST_AsMVTGeom(the_geom_webmercator, ST_TileEnvelope($1,$2,$3), 4096, 256, true) AS mvtgeometry
                            FROM ({query}) as data 
                        WHERE ST_AsMVTGeom(the_geom_webmercator, ST_TileEnvelope($1,$2,$3),4096,0,true) IS NOT NULL) AS tile;
               """

    logging.info(prepared)
    return(prepared)

async def Query(app, query, asJson = True):
    logging.debug(f"{query}")
    async with app['db'].acquire() as conn:
        fetchQuery = await conn.execute(query)
        results = await fetchQuery.fetchall()
       
    if not asJson:
        response = [dict(q) for q in results]
        response = io.BytesIO(response[0]['tile']).getvalue()
    else:
        response = [{column: value for column, value in dict(rowproxy).items()} for rowproxy in results]
    
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

####TILES endpoint
@cache()
@docs(tags=['tiles endpoint'],
      summary='Test method summary',
      description='Test method description')
@request_schema(RequestTileSchema())
@routes.get('/v1/tiles/{z:([0-9]+)}/{x:([0-9]+)}/{y:([0-9]+)}.pbf')
async def get_mvt(request):
    headers = {"Content-Type":"application/x-protobuf",
    "Content-Disposition": "attachment",
    "Access-Control-Allow-Origin": "*"
    }
    user_query = f"{request.query['sql']}".strip()
    query_id = uuid.uuid5(uuid.NAMESPACE_DNS, user_query)
    #prepared = await GeneratePrepared(query, query_id)
    logging.info(f"[Tile query]: {user_query}")
    logging.info(f"[Tile query]: {query_id}")
    
    #final_query = f"EXECUTE gettile_{query_id}({request.query['sql']}, {request.match_info['z']}, {request.match_info['x']}, {request.match_info['y']});"
    final_query = f"""SELECT ST_ASMVT(tile.*, 'layer0', 4096, 'mvtgeometry', 'ogc_fid') as tile
                  FROM (SELECT *, ST_AsMVTGeom(the_geom_webmercator, ST_TileEnvelope({request.match_info['z']},{request.match_info['x']},{request.match_info['y']}), 4096, 256, true) AS mvtgeometry
                            FROM (select *, st_transform(geom, 3857) as the_geom_webmercator from mgis_point_data) as data 
                        WHERE ST_AsMVTGeom(the_geom_webmercator, ST_TileEnvelope({request.match_info['z']},{request.match_info['x']},{request.match_info['y']}),4096,0,true) IS NOT NULL) AS tile;
                    """
    logging.info(f"[Tile query]: {final_query}")
    
    content =await Query(request.app, final_query, asJson = False)

    return web.Response(body= content, headers=headers)

####QUERY endpoint
@cache()
@docs(tags=['query endpoint'],
      summary='Allow queries to the selected database',
      description='Test method description')
@request_schema(RequestSchema())
@response_schema(ResponseSchema(), 200)                              
@routes.get('/v1/query', name='test')
async def hello_world(request):
    try:
        headers = {
            "Content-Type":"application/json",
                "Access-Control-Allow-Origin": "*"
                }
        final_query = f"{request.query['sql']}"
        output = await Query(request.app, final_query)
        logging.debug(f"[query:output]: {output}")
        logging.debug(f"[query:output]: {type(output)}") 
        logging.debug(f"[query:output]: {type(output)}") 
        
        return web.Response(text=json.dumps({'data':output}, cls=JSONDateEncoder),
                                    headers=headers,
                                    status=200)
    except Exception as e:
        logging.error(e)
        raise web.HTTPInternalServerError(text=json.dumps({'detail':str(e)}), content_type="application/json")
