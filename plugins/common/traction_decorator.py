"""
A message decorator for threads.

A thread decorator identifies a message that may require additional
context from previous messages.
"""

from typing import List, Optional

from marshmallow import EXCLUDE, fields

from aries_cloudagent.messaging.models.base import BaseModel, BaseModelSchema
from aries_cloudagent.messaging.valid import UUIDFour


class TractionDecorator(BaseModel):

    class Meta:
        schema_class = "TractionDecoratorSchema"

    def __init__(
        self,
        *,
        external_reference_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ):

        super().__init__()
        self._external_reference_id = external_reference_id
        self._tags = tags

    @property
    def external_reference_id(self):
        return self._external_reference_id

    @property
    def tags(self):
        return self._tags


class TractionDecoratorSchema(BaseModelSchema):

    class Meta:

        model_class = TractionDecorator
        unknown = EXCLUDE

    external_reference_id = fields.Str(
        required=False,
        allow_none=True,
        description="ID in external system",
        example=UUIDFour.EXAMPLE,  # typically a UUID4 but not necessarily
    )
    tags = fields.List(
        fields.Str(description="Tags for grouping and categorizing"),
        data_key="tags",
        required=True,
        description="List of tags",
    )
