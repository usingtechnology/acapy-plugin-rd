"""Connection handling admin routes."""

import functools
import json

from aiohttp import web
from aiohttp_apispec import (
    docs,
    match_info_schema,
    querystring_schema,
    request_schema,
    response_schema,
)

from marshmallow import fields, validate, validates_schema

from aries_cloudagent.admin.request_context import AdminRequestContext
from aries_cloudagent.connections.models.conn_record import ConnRecord, ConnRecordSchema
from aries_cloudagent.messaging.models.base import BaseModelError
from aries_cloudagent.messaging.models.openapi import OpenAPISchema
from aries_cloudagent.messaging.valid import (
    ENDPOINT,
    INDY_DID,
    INDY_RAW_PUBLIC_KEY,
    UUIDFour,
)
from aries_cloudagent.storage.error import StorageError, StorageNotFoundError
from aries_cloudagent.wallet.error import WalletError

from aries_cloudagent.protocols.connections.v1_0.manager import ConnectionManager, ConnectionManagerError
from aries_cloudagent.protocols.connections.v1_0.message_types import SPEC_URI
from aries_cloudagent.protocols.connections.v1_0.messages.connection_invitation import (
    ConnectionInvitation,
    ConnectionInvitationSchema,
)

from aries_cloudagent.protocols.connections.v1_0.routes import (
	connections_list,
	connections_retrieve,
	connections_metadata,
	connections_metadata_set,
	connections_endpoints,
	connections_create_static,
	connections_create_invitation,
	connections_receive_invitation,
	connections_accept_invitation,
	connections_accept_request,
	connections_establish_inbound,
	connections_remove,
	CreateInvitationRequestSchema,
	CreateInvitationQueryStringSchema,
	InvitationResultSchema,
	ReceiveInvitationQueryStringSchema,
	ReceiveInvitationRequestSchema,
	ConnRecordSchema
	)


def traction_deco(func):
    @functools.wraps(func)
    async def wrapper(request):
        print('> traction_deco')
        print(request)
        params = await request.json()
        try:
            print('... calling...')
            ret = await func(request)
            return ret
            # body = json.loads(ret.body)

            #if params["traction"]:
            #	body["~traction"] = params["traction"]

            # ideally use something like Dispatcher.make_message when we have agentmessages
            # obj = BasicMessage.deserialize(body)
            #print(obj)
            #obj._decorators["traction"] = TractionDecorator(external_reference_id=params["external_reference_id"], tags=params["tags"])
            #return web.json_response(body)
        finally:
            print('< traction_deco')

    return wrapper


class TractionFieldsSchema(OpenAPISchema):
    external_reference_id = fields.Str(description="External Reference Id", example="id_xyz", required=False)
    tags = fields.List(
        fields.Str(description="Tags for grouping and categorizing"),
        data_key="tags",
        required=False,
        description="List of tags",
    )

class TractionSchema(OpenAPISchema):
    traction = fields.Nested(TractionFieldsSchema, description="Traction fields", required=False)


class TractionCreateInvitationRequestSchema(CreateInvitationRequestSchema, TractionSchema):
    """Request schema for creating connection."""



class TractionReceiveInvitationRequestSchema(ReceiveInvitationRequestSchema, TractionSchema):
    """Request schema for receiving connection."""

@docs(
    tags=["connection"],
    summary="Create a new connection invitation",
)
@querystring_schema(CreateInvitationQueryStringSchema())
@request_schema(CreateInvitationRequestSchema())
@response_schema(InvitationResultSchema(), 200, description="")
@traction_deco
async def traction_connections_create_invitation(request: web.BaseRequest):
    return await connections_create_invitation(request) 



async def register(app: web.Application):
    """Register routes."""

    app.add_routes(
        [
            web.get("/connections", connections_list, allow_head=False),
            web.get("/connections/{conn_id}", connections_retrieve, allow_head=False),
            web.get(
                "/connections/{conn_id}/metadata",
                connections_metadata,
                allow_head=False,
            ),
            web.post("/connections/{conn_id}/metadata", connections_metadata_set),
            web.get(
                "/connections/{conn_id}/endpoints",
                connections_endpoints,
                allow_head=False,
            ),
            web.post("/connections/create-static", connections_create_static),
            web.post("/connections/create-invitation", traction_connections_create_invitation),
            web.post("/connections/receive-invitation", connections_receive_invitation),
            web.post(
                "/connections/{conn_id}/accept-invitation",
                connections_accept_invitation,
            ),
            web.post(
                "/connections/{conn_id}/accept-request",
                connections_accept_request,
            ),
            web.post(
                "/connections/{conn_id}/establish-inbound/{ref_id}",
                connections_establish_inbound,
            ),
            web.delete("/connections/{conn_id}", connections_remove),
        ]
    )


def post_process_routes(app: web.Application):
    """Amend swagger API."""

    # Add top-level tags description
    if "tags" not in app._state["swagger_dict"]:
        app._state["swagger_dict"]["tags"] = []
    app._state["swagger_dict"]["tags"].append(
        {
            "name": "connection",
            "description": "Connection management",
            "externalDocs": {"description": "Specification", "url": SPEC_URI},
        }
    )
