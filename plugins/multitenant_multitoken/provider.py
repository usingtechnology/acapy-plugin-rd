"""Profile manager for multitenancy."""

import logging

from aries_cloudagent.config.provider import BaseProvider
from aries_cloudagent.config.settings import BaseSettings
from aries_cloudagent.config.injector import BaseInjector
from aries_cloudagent.config.base import InjectionError
from aries_cloudagent.utils.classloader import ClassLoader, ClassNotFoundError

from aries_cloudagent.multitenant.manager_provider import MultitenantManagerProvider

LOGGER = logging.getLogger(__name__)


class TractionMultitenantManagerProvider(MultitenantManagerProvider):
    """
    Multitenant manager provider.

    Decides which manager to use based on the settings.
    """

    askar_profile_manager_path = (
        "aries_cloudagent.multitenant."
        "askar_profile_manager.AskarProfileMultitenantManager"
    )
    MANAGER_TYPES = {
        "basic": "plugins.multitenant_multitoken.manager.TractionMultitenantManager",
        "askar-profile": askar_profile_manager_path,
    }

    def provide(self, settings: BaseSettings, injector: BaseInjector):
        """Create the multitenant manager instance."""

        multitenant_wallet_type = "multitenant.wallet_type"
        manager_type = settings.get_value(
            multitenant_wallet_type, default="basic"
        ).lower()

        manager_class = self.MANAGER_TYPES.get(manager_type, manager_type)

        if manager_class not in self._inst:
            LOGGER.info("Create multitenant manager: %s", manager_type)
            try:
                self._inst[manager_class] = ClassLoader.load_class(manager_class)(
                    self.root_profile
                )
            except ClassNotFoundError as err:
                raise InjectionError(
                    f"Unknown multitenant manager type: {manager_type}"
                ) from err

        return self._inst[manager_class]
