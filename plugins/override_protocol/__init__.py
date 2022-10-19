"""ACA-Py Pickup Protocol Plugin."""

import os
import logging

from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.core.protocol_registry import ProtocolRegistry

async def setup(context: InjectionContext):
    """Setup plugin."""
    protocol_registry = context.inject(ProtocolRegistry)
    assert protocol_registry
    print("> override_protocol loading...")