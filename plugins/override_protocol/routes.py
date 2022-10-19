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
            body = json.loads(ret.body)

            if params["traction"]:
            	body["~traction"] = params["traction"]

            # ideally use something like Dispatcher.make_message when we have agentmessages
            # obj = BasicMessage.deserialize(body)
            #print(obj)
            #obj._decorators["traction"] = TractionDecorator(external_reference_id=params["external_reference_id"], tags=params["tags"])
            return web.json_response(body)
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
@request_schema(TractionCreateInvitationRequestSchema())
@response_schema(InvitationResultSchema(), 200, description="")
@traction_deco
async def traction_connections_create_invitation(request: web.BaseRequest):
    """
    Request handler for creating a new connection invitation.

    Args:
        request: aiohttp request object

    Returns:
        The connection invitation details

    """
    context: AdminRequestContext = request["context"]
    auto_accept = json.loads(request.query.get("auto_accept", "null"))
    alias = request.query.get("alias")
    public = json.loads(request.query.get("public", "false"))
    multi_use = json.loads(request.query.get("multi_use", "false"))
    body = await request.json() if request.body_exists else {}
    my_label = body.get("my_label")
    recipient_keys = body.get("recipient_keys")
    service_endpoint = body.get("service_endpoint")
    routing_keys = body.get("routing_keys")
    metadata = body.get("metadata")
    mediation_id = body.get("mediation_id")

    if public and not context.settings.get("public_invites"):
        raise web.HTTPForbidden(
            reason="Configuration does not include public invitations"
        )
    profile = context.profile
    base_url = profile.settings.get("invite_base_url")

    connection_mgr = ConnectionManager(profile)
    try:
        (connection, invitation) = await connection_mgr.create_invitation(
            my_label=my_label,
            auto_accept=auto_accept,
            public=public,
            multi_use=multi_use,
            alias=alias,
            recipient_keys=recipient_keys,
            my_endpoint=service_endpoint,
            routing_keys=routing_keys,
            metadata=metadata,
            mediation_id=mediation_id,
        )

        result = {
            "connection_id": connection and connection.connection_id,
            "invitation": invitation.serialize(),
            "invitation_url": invitation.to_url(base_url),
        }
    except (ConnectionManagerError, StorageError, BaseModelError) as err:
        raise web.HTTPBadRequest(reason=err.roll_up) from err

    if connection and connection.alias:
        result["alias"] = connection.alias

    return web.json_response(result)
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
