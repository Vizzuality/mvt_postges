"""Main Script"""
import os
from aiohttp import web
import asyncio
from app import init



if __name__ == "__main__":
    # Make this prepared statement from the tm2source
    loop = asyncio.get_event_loop()
    app = loop.run_until_complete(init(loop))
    web.run_app(app, 
    			host=os.getenv('HOST'), 
    			port=os.getenv('PORT'))