from foglamp.admin_api.app_builder import build as build_app
import asyncio


def start():
    """Create a http server for REST listening on port 8081"""
    # TODO Read port from config (but might use nginx in production especially for https and reverse proxy)

    loop = asyncio.get_event_loop()
    f = loop.create_server(build_app().make_handler(), '0.0.0.0', 8081)
    loop.create_task(f)
