"""ACA-Py Pickup Protocol Plugin."""

import os
import logging

from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.core.protocol_registry import ProtocolRegistry
\
from aries_cloudagent.protocols.connections.v1_0.message_types import MESSAGE_TYPES


async def setup(context: InjectionContext):
    """Setup plugin."""
    protocol_registry = context.inject(ProtocolRegistry)
    assert protocol_registry
    print("> override_protocol loading...")
    print("> register_message_types for connections v1_0...")
    protocol_registry.register_message_types(MESSAGE_TYPES)