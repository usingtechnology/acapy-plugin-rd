import logging
import jwt


from aries_cloudagent.config.wallet import wallet_config
from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.wallet.models.wallet_record import WalletRecord
from aries_cloudagent.multitenant.base import BaseMultitenantManager, MultitenantManagerError
from aries_cloudagent.multitenant.manager import MultitenantManager

from datetime import datetime, timedelta, timezone


from typing import List, Optional, cast

from aries_cloudagent.core.profile import (
    Profile,
    ProfileSession,
)
from aries_cloudagent.messaging.responder import BaseResponder
from aries_cloudagent.config.injection_context import InjectionContext
from aries_cloudagent.wallet.models.wallet_record import WalletRecord, WalletRecordSchema
from aries_cloudagent.wallet.base import BaseWallet
from aries_cloudagent.core.error import BaseError
from aries_cloudagent.protocols.routing.v1_0.manager import RouteNotFoundError, RoutingManager
from aries_cloudagent.protocols.routing.v1_0.models.route_record import RouteRecord
from aries_cloudagent.transport.wire_format import BaseWireFormat
from aries_cloudagent.storage.base import BaseStorage
from aries_cloudagent.storage.error import StorageNotFoundError
from aries_cloudagent.protocols.coordinate_mediation.v1_0.manager import (
    MediationManager,
    MediationRecord,
)
from marshmallow.utils import EXCLUDE
from aries_cloudagent.multitenant.error import WalletKeyMissingError

LOGGER = logging.getLogger(__name__)


class TokensWalletRecord(WalletRecord):
    class Meta:
        """WalletRecord metadata."""

        schema_class = "TokensWalletRecordSchema"

    def __init__(
        self,
        *,
        wallet_id: str = None,
        key_management_mode: str = None,
        settings: dict = None,
        # MTODO: how to make this a tag without making it
        # a constructor param
        wallet_name: str = None,
        jwt_iat: Optional[int] = None,
        issued_at_claims: Optional[List] = [],
        **kwargs,
    ):
        """Initialize a new WalletRecord."""
        super().__init__(wallet_id=wallet_id, key_management_mode=key_management_mode, settings=settings, wallet_name=wallet_name, jwt_iat=jwt_iat, **kwargs)
        self._issued_at_claims = issued_at_claims
    
    @property
    def issued_at_claims(self):
        return self._issued_at_claims

    def add_issued_at_claims(self, iat):
        self._issued_at_claims.append(iat)


class TokensWalletRecordSchema(WalletRecordSchema):
    """Schema to allow serialization/deserialization of record."""

    class Meta:
        """WalletRecordSchema metadata."""

        model_class = TokensWalletRecord
        unknown = EXCLUDE


class TractionMultitenantManager(MultitenantManager):

    def __init__(self, profile: Profile):
        super().__init__(profile)

    async def get_wallet_profile(
        self,
        base_context: InjectionContext,
        wallet_record: WalletRecord,
        extra_settings: dict = {},
        *,
        provision=False,
    ) -> Profile:
        LOGGER.info('> get_wallet_profile!!!')
        return await super().get_wallet_profile(base_context=base_context, wallet_record=wallet_record, extra_settings=extra_settings, provision=provision)
 

    async def remove_wallet_profile(self, profile: Profile):
        LOGGER.info('> remove_wallet_profile!!!')
        return super().remove_wallet_profile(profile)

    async def create_auth_token(
        self, wallet_record: WalletRecord, wallet_key: str = None) -> str:
        LOGGER.info('> create_auth_token!!!')
        # create and get new token from super class...
        # token = await super().create_auth_token(wallet_record=wallet_record, wallet_key=wallet_key)
        async with self._profile.session() as session:
            tokens_wallet_record = await TokensWalletRecord.retrieve_by_id(session, wallet_record.wallet_id)
            LOGGER.info(tokens_wallet_record)

        iat = datetime.now(tz=timezone.utc)
        exp = iat + timedelta(minutes=1)

        jwt_payload = {"wallet_id": wallet_record.wallet_id, "iat": iat, "exp": exp}
        jwt_secret = self._profile.settings.get("multitenant.jwt_secret")

        if tokens_wallet_record.requires_external_key:
            if not wallet_key:
                raise WalletKeyMissingError()

            jwt_payload["wallet_key"] = wallet_key

        encoded = jwt.encode(jwt_payload, jwt_secret, algorithm="HS256")
        LOGGER.info(encoded)    
        decoded = jwt.decode(encoded, jwt_secret, algorithms=["HS256"])
        LOGGER.info(decoded)
        token = encoded

        LOGGER.info(f"wallet.issued_at_claims = {tokens_wallet_record.issued_at_claims}")
        # Store iat for verification later on
        tokens_wallet_record.jwt_iat = decoded.get("iat")
        tokens_wallet_record.add_issued_at_claims(decoded.get("iat"))
        LOGGER.info(f"adding iat... {tokens_wallet_record.issued_at_claims}")

        async with self._profile.session() as session:
            await tokens_wallet_record.save(session)

        async with self._profile.session() as session:
            tokens_wallet_record = await TokensWalletRecord.retrieve_by_id(session, wallet_record.wallet_id)
            LOGGER.info(tokens_wallet_record)

        # return this token...    
        return token

    async def get_profile_for_token(
            self, context: InjectionContext, token: str) -> Profile:
        LOGGER.info('> get_profile_for_token!!!')
        # return await super().get_profile_for_token(context=context, token=token)
        """Get the profile associated with a JWT header token.

        Args:
            context: The context to use for profile creation
            token: The token

        Raises:
            WalletKeyMissingError: If the wallet_key is missing for an unmanaged wallet
            InvalidTokenError: If there is an exception while decoding the token

        Returns:
            Profile associated with the token

        """
        jwt_secret = self._profile.context.settings.get("multitenant.jwt_secret")
        extra_settings = {}

        try:
            token_body = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        except jwt.exceptions.ExpiredSignatureError as err:
            LOGGER.error("Expired Signature... clean up claims")
            # ignore expiry so we can get the iat...
            token_body = jwt.decode(token, jwt_secret, algorithms=["HS256"], options={"verify_exp": False})
            wallet_id = token_body.get("wallet_id")
            iat = token_body.get("iat")
            async with self._profile.session() as session:
                wallet = await TokensWalletRecord.retrieve_by_id(session, wallet_id)
                LOGGER.info(wallet)
                wallet.issued_at_claims.remove(iat)
                await wallet.save(session)
            
            async with self._profile.session() as session:
                wallet = await TokensWalletRecord.retrieve_by_id(session, wallet_id)
                LOGGER.info(wallet)

            raise err

        wallet_id = token_body.get("wallet_id")
        wallet_key = token_body.get("wallet_key")
        iat = token_body.get("iat")

        async with self._profile.session() as session:
            wallet = await TokensWalletRecord.retrieve_by_id(session, wallet_id)
            LOGGER.info(wallet)

        if wallet.requires_external_key:
            if not wallet_key:
                raise WalletKeyMissingError()

            extra_settings["wallet.key"] = wallet_key

        token_valid = False    
        for claim in wallet.issued_at_claims:
            LOGGER.info(f"claim = {claim}, iat = {iat}")
            if claim == iat:
                LOGGER.info(f"claim = {claim}, iat = {iat} - matched!!!")
                token_valid = True

        if not token_valid:
            raise MultitenantManagerError("Token not valid")

        profile = await self.get_wallet_profile(context, wallet, extra_settings)

        return profile
