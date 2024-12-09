# Copyright (c) 2024 AccelByte Inc. All Rights Reserved.
# This is licensed software from AccelByte Inc, for limitations
# and restrictions contact your company contract manager.

import json

from base64 import urlsafe_b64encode
from datetime import datetime, timezone
from hashlib import sha256
from hmac import new as hmac_new
from logging import Logger
from random import getrandbits
from typing import Any, Dict, Optional

from google.protobuf.json_format import MessageToJson
from grpc import StatusCode

from accelbyte_grpc_plugin.utils import create_aio_rpc_error

from ..proto.service_pb2 import (
    GenerateVivoxTokenRequest,
    GenerateVivoxTokenRequestType,
    GenerateVivoxTokenRequestChannelType,
    GenerateVivoxTokenResponse,
    DESCRIPTOR,
)
from ..proto.service_pb2_grpc import ServiceServicer


encoding: str = "utf-8"

vivox_channel_types: Dict[Any, str] = {
    GenerateVivoxTokenRequestChannelType.echo: "e",
    GenerateVivoxTokenRequestChannelType.positional: "d",
    GenerateVivoxTokenRequestChannelType.nonpositional: "g",
}


class VivoxTokenProvider:
    def __init__(
        self,
        issuer: str,
        signing_key: str,
        channel_prefix: str = "confctl",
        domain: str = "tla.vivox.com",
        token_duration: int = 90,
        **kwargs
    ) -> None:
        self.issuer = issuer.strip('"')
        self.signing_key = signing_key.strip('"')
        self.channel_prefix = channel_prefix.strip('"')
        self.domain = domain.strip('"')
        self.token_duration = token_duration

    def format_channel_name(self, channel_id: str, channel_type: str) -> str:
        return f"sip:{self.channel_prefix}-{channel_type}-{self.issuer}.{channel_id}@{self.domain}"

    def format_user_name(self, user_id: str) -> str:
        return f"sip:.{self.issuer}.{user_id}.@{self.domain}"

    def generate_token(
        self,
        vxa: str,
        f: str,
        exp: Optional[int] = None,
        vxi: Optional[str] = None,
        t: Optional[str] = None,
        sub: Optional[str] = None,
    ) -> bytes:
        if not exp:
            exp = self.get_exp()
        if not vxi:
            vxi = self.get_vxi()
        return self.format_token(
            key=self.signing_key,
            iss=self.issuer,
            exp=exp,
            vxa=vxa,
            vxi=vxi,
            f=f,
            t=t,
            sub=sub,
        )

    @staticmethod
    def format_token(
        key: str,
        iss: str,
        exp: int,
        vxa: str,
        vxi: str,
        f: str,
        t: Optional[str] = None,
        sub: Optional[str] = None,
    ) -> bytes:
        def b64url(s: bytes) -> bytes:
            return urlsafe_b64encode(s=s).rstrip("=".encode(encoding=encoding))

        # Create dictionary of claims.
        claims = {
            "iss": iss,
            "exp": exp,
            "vxa": vxa,
            "vxi": vxi,
            "f": f,
        }

        if t:
            claims["t"] = t

        if sub:
            claims["sub"] = sub

        # Create header.
        header = b64url("{}".encode(encoding=encoding))

        # Encode claims payload.
        payload = b64url(json.dumps(claims).encode(encoding=encoding))

        # Join segments to prepare for signing.
        segments = [header, payload]
        msg = b".".join(segments)

        # Sign token with key and HMACSHA256.
        sig = hmac_new(
            key=key.encode(encoding=encoding), msg=msg, digestmod=sha256
        ).digest()
        segments.append(b64url(sig))

        # Join all 3 parts of the token with . and return.
        return b".".join(segments)

    @staticmethod
    def generate_uid() -> int:
        return getrandbits(16)

    @staticmethod
    def get_unix_timestamp() -> int:
        return int(datetime.now(tz=timezone.utc).timestamp())

    def get_exp(self) -> int:
        return self.get_unix_timestamp() + self.token_duration

    def get_vxi(self) -> int:
        return self.generate_uid()


class AsyncVivoxService(ServiceServicer):
    full_name: str = DESCRIPTOR.services_by_name["Service"].full_name

    def __init__(
        self,
        logger: Logger,
        issuer: str,
        signing_key: str,
        channel_prefix: str = "confctl",
        domain: str = "tla.vivox.com",
        token_duration: int = 90,
        **kwargs
    ) -> None:
        self.logger = logger

        self.provider = VivoxTokenProvider(
            issuer=issuer,
            signing_key=signing_key,
            channel_prefix=channel_prefix,
            domain=domain,
            token_duration=token_duration,
        )

    # noinspection PyShadowingBuiltins
    def log_payload(self, format: str, payload: Any) -> None:
        if not self.logger:
            return
        payload_json = MessageToJson(payload, preserving_proto_field_name=True)
        self.logger.info(format % payload_json)

    async def GenerateVivoxToken(self, request: GenerateVivoxTokenRequest, context: Any) -> GenerateVivoxTokenResponse:
        self.log_payload(f"{self.GenerateVivoxToken.__name__} request: %s", request)

        if not request.type:
            raise create_aio_rpc_error("type not found", StatusCode.INVALID_ARGUMENT)

        if not request.username:
            raise create_aio_rpc_error("username not found", StatusCode.INVALID_ARGUMENT)

        if request.type in (GenerateVivoxTokenRequestType.kick,) and not request.targetUsername:
            raise create_aio_rpc_error("targetUsername not found", StatusCode.INVALID_ARGUMENT)

        if request.type in (
            GenerateVivoxTokenRequestType.join,
            GenerateVivoxTokenRequestType.join_muted,
            GenerateVivoxTokenRequestType.kick
        ) and not request.channelId:
            raise create_aio_rpc_error("channelId not found", StatusCode.INVALID_ARGUMENT)

        if request.type in (
            GenerateVivoxTokenRequestType.join,
            GenerateVivoxTokenRequestType.join_muted,
            GenerateVivoxTokenRequestType.kick
        ) and not request.channelType:
            raise create_aio_rpc_error("channelType not found", StatusCode.INVALID_ARGUMENT)

        channel_type = vivox_channel_types.get(request.channelType, "")

        t = self.provider.format_channel_name(channel_id=request.channelId, channel_type=channel_type)

        generate_token_kwargs = {
            "vxa": GenerateVivoxTokenRequestType.Name(request.type),
            "f":  self.provider.format_user_name(user_id=request.username)
        }

        response = GenerateVivoxTokenResponse()

        if request.type == GenerateVivoxTokenRequestType.login:
            token = self.provider.generate_token(**generate_token_kwargs)
        elif request.type in (GenerateVivoxTokenRequestType.join, GenerateVivoxTokenRequestType.join_muted):
            token = self.provider.generate_token(t=t, **generate_token_kwargs)
            response.uri = t
        elif request.type == GenerateVivoxTokenRequestType.kick:
            token = self.provider.generate_token(
                t=t, sub=self.provider.format_user_name(request.targetUsername), **generate_token_kwargs,
            )
            response.uri = t
        else:
            raise create_aio_rpc_error(f"unimplemented type: {request.type}", StatusCode.UNIMPLEMENTED)

        response.accessToken = token.decode(encoding=encoding)

        self.log_payload(f"{self.GenerateVivoxToken.__name__} response: %s", response)

        return response
