# Copyright (c) 2024 AccelByte Inc. All Rights Reserved.
# This is licensed software from AccelByte Inc, for limitations
# and restrictions contact your company contract manager.

import asyncio
import logging

from argparse import ArgumentParser
from logging import Logger
from typing import List, Optional

from accelbyte_py_sdk.core import (
    AccelByteSDK,
    DictConfigRepository,
    InMemoryTokenRepository,
    HttpxHttpClient,
)
from accelbyte_py_sdk.services import auth as auth_service

from environs import Env

from accelbyte_grpc_plugin.app import (
    App,
    AppOption,
    AppOptionGRPCInterceptor,
    AppOptionGRPCService,
)
from accelbyte_grpc_plugin.utils import instrument_sdk_http_client

from app.proto.service_pb2_grpc import add_ServiceServicer_to_server

from app.services.vivox_service import AsyncVivoxService
from app.utils import create_env

DEFAULT_APP_PORT: int = 6565

DEFAULT_AB_BASE_URL: str = "https://test.accelbyte.io"
DEFAULT_AB_NAMESPACE: str = "accelbyte"

DEFAULT_ENABLE_HEALTH_CHECK: bool = True
DEFAULT_ENABLE_PROMETHEUS: bool = True
DEFAULT_ENABLE_REFLECTION: bool = True
DEFAULT_ENABLE_ZIPKIN: bool = True

DEFAULT_PLUGIN_GRPC_SERVER_AUTH_ENABLED: bool = False
DEFAULT_PLUGIN_GRPC_SERVER_AUTH_RESOURCE: Optional[str] = None
DEFAULT_PLUGIN_GRPC_SERVER_AUTH_ACTION: Optional[int] = None

DEFAULT_PLUGIN_GRPC_SERVER_LOGGING_ENABLED: bool = False
DEFAULT_PLUGIN_GRPC_SERVER_METRICS_ENABLED: bool = True


async def main(port: int, **kwargs) -> None:
    env = create_env(**kwargs)

    logger = logging.getLogger("app")
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())

    config = DictConfigRepository(dict(env.dump()))
    token = InMemoryTokenRepository()
    http = HttpxHttpClient()
    http.client.follow_redirects = True

    sdk = AccelByteSDK()
    sdk.initialize(
        options={
            "config": config,
            "token": token,
            "http": http,
        }
    )

    instrument_sdk_http_client(sdk=sdk, logger=logger)

    _, error = await auth_service.login_client_async(sdk=sdk)
    if error:
        raise Exception(str(error))
    
    sdk.timer = auth_service.LoginClientTimer(2880, repeats=-1, autostart=True, sdk=sdk)

    options = create_options(sdk=sdk, env=env, logger=logger)

    ds_provider = env("DS_PROVIDER", "DEMO")
    service = AsyncVivoxService(
        logger=logger,
        issuer=env("VIVOX_ISSUER"),
        signing_key=env("VIVOX_SIGNING_KEY"),
        channel_prefix=env("VIVOX_CHANNEL_PREFIX", "confctl"),
        domain=env("VIVOX_DOMAIN", "tla.vivox.com"),
        token_duration=env.int("VIVOX_TOKEN_DURATION", 90),
    )
    options.append(
        AppOptionGRPCService(
            full_name=service.full_name,
            service=service,
            add_service_fn=add_ServiceServicer_to_server,
        )
    )

    app = App(port=port, env=env, logger=logger, options=options)
    await app.run()


def parse_args():
    parser = ArgumentParser()
    parser.add_argument(
        "-p",
        "--port",
        default=DEFAULT_APP_PORT,
        type=int,
        required=False,
        help="[P]ort",
    )
    result = vars(parser.parse_args())
    return result


def create_options(sdk: AccelByteSDK, env: Env, logger: Logger) -> List[AppOption]:
    options: List[AppOption] = []

    with env.prefixed("AB_"):
        namespace = env.str("NAMESPACE", DEFAULT_AB_NAMESPACE)

    with env.prefixed("ENABLE_"):
        if env.bool("HEALTH_CHECK", DEFAULT_ENABLE_HEALTH_CHECK):
            from accelbyte_grpc_plugin.options.grpc_health_check import (
                AppOptionGRPCHealthCheck,
            )

            options.append(AppOptionGRPCHealthCheck())
        if env.bool("PROMETHEUS", DEFAULT_ENABLE_PROMETHEUS):
            from accelbyte_grpc_plugin.options.prometheus import AppOptionPrometheus

            options.append(AppOptionPrometheus())
        if env.bool("REFLECTION", DEFAULT_ENABLE_REFLECTION):
            from accelbyte_grpc_plugin.options.grpc_reflection import (
                AppOptionGRPCReflection,
            )

            options.append(AppOptionGRPCReflection())
        if env.bool("ZIPKIN", DEFAULT_ENABLE_ZIPKIN):
            from accelbyte_grpc_plugin.options.zipkin import AppOptionZipkin

            options.append(AppOptionZipkin())

    with env.prefixed("PLUGIN_GRPC_SERVER_"):
        with env.prefixed("AUTH_"):
            if env.bool("ENABLED", DEFAULT_PLUGIN_GRPC_SERVER_AUTH_ENABLED):
                from accelbyte_py_sdk.token_validation.caching import (
                    CachingTokenValidator,
                )
                from accelbyte_grpc_plugin.interceptors.authorization import (
                    AuthorizationServerInterceptor,
                )

                options.append(
                    AppOptionGRPCInterceptor(
                        interceptor=AuthorizationServerInterceptor(
                            resource=env.str(
                                "RESOURCE", DEFAULT_PLUGIN_GRPC_SERVER_AUTH_RESOURCE
                            ),
                            action=env.int(
                                "ACTION", DEFAULT_PLUGIN_GRPC_SERVER_AUTH_ACTION
                            ),
                            namespace=namespace,
                            token_validator=CachingTokenValidator(sdk=sdk),
                        )
                    )
                )
        if env.bool("LOGGING_ENABLED", DEFAULT_PLUGIN_GRPC_SERVER_LOGGING_ENABLED):
            from accelbyte_grpc_plugin.interceptors.logging import (
                LoggingServerInterceptor,
            )

            options.append(
                AppOptionGRPCInterceptor(
                    interceptor=LoggingServerInterceptor(logger=logger)
                )
            )

        if env.bool("METRICS_ENABLED", DEFAULT_PLUGIN_GRPC_SERVER_METRICS_ENABLED):
            from accelbyte_grpc_plugin.interceptors.metrics import (
                MetricsServerInterceptor,
            )

            options.append(
                AppOptionGRPCInterceptor(interceptor=MetricsServerInterceptor())
            )

    return options


def run() -> None:
    asyncio.run(main(**parse_args()))


if __name__ == "__main__":
    run()
