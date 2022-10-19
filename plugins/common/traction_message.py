from typing import Union

from aries_cloudagent.messaging.agent_message import AgentMessage

from .traction_decorator import TractionDecorator

class TractionMessage(AgentMessage):


    def __init__(
        self,
        **kwargs,
    ):

        super().__init__(**kwargs)
        self._decorators["traction"] = TractionDecorator()

    @property
    def _traction(self) -> TractionDecorator:
        return self._decorators.get("traction")

    @_traction.setter
    def _traction(self, val: Union[TractionDecorator, dict]):
        if val is None:
            self._decorators.pop("traction", None)
        else:
            self._decorators["traction"] = val