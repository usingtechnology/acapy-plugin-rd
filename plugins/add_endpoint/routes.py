import os

from aiohttp import web
from aiohttp_apispec import docs, match_info_schema, request_schema, response_schema

from marshmallow import fields

from aries_cloudagent.admin.request_context import AdminRequestContext
from aries_cloudagent.connections.models.conn_record import ConnRecord
from aries_cloudagent.messaging.models.openapi import OpenAPISchema
from aries_cloudagent.messaging.valid import UUIDFour
from aries_cloudagent.storage.error import StorageNotFoundError

from aries_cloudagent.protocols.basicmessage.v1_0.message_types import SPEC_URI


class DemoModuleResponseSchema(OpenAPISchema):
    """Response schema for demo"""


class DemoModuleSchema(OpenAPISchema):
    """Request schema for demo"""
    content = fields.Str(description="Message content", example="World")


@docs(tags=["demo"], summary="do some demo")
@request_schema(DemoModuleSchema())
@response_schema(DemoModuleResponseSchema(), 200, description="")
async def hello_world(request: web.BaseRequest):
    print(request)
    params = await request.json()
    return web.json_response({"message": f"Hello {params['content']}!"})

async def register(app: web.Application):
    """Register routes."""
    print("...now we are registering a route for demo...")
    app.add_routes(
        [web.post("/demo/hello-world", hello_world)]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "demo",
            "description": "Simple demo",
            "externalDocs": {"description": "Specification", "url": SPEC_URI},
        }
    )
