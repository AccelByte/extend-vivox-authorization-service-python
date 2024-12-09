# Copyright (c) 2024 AccelByte Inc. All Rights Reserved.
# This is licensed software from AccelByte Inc, for limitations
# and restrictions contact your company contract manager.

import jwt
import logging

from unittest import IsolatedAsyncioTestCase

from app.proto.service_pb2 import (
    GenerateVivoxTokenRequest,
    GenerateVivoxTokenRequestType,
    GenerateVivoxTokenRequestChannelType,
)
from app.services.vivox_service import AsyncVivoxService

logger = logging.getLogger("tests")
logger.setLevel(logging.WARNING)
logger.addHandler(logging.StreamHandler())


class AsyncServiceTestCase(IsolatedAsyncioTestCase):
    @staticmethod
    def decode_token(token: str) -> dict:
        return jwt.decode(
            token, algorithms=["HS256"], options={"verify_signature": False},
        )

    async def asyncSetUp(self) -> None:
        self.service = AsyncVivoxService(
            logger=logger,
            issuer="blindmelon-AppName-dev",
            signing_key="secret!",
            domain="tla.vivox.com",
        )

    async def test_generate_vivox_token_login(self) -> None:
        # arrange
        request = GenerateVivoxTokenRequest()
        request.type = GenerateVivoxTokenRequestType.login
        request.username = "jerky"

        # monkey-patch
        self.service.provider.get_exp = lambda: 1600349400
        self.service.provider.get_vxi = lambda: 933000

        # act
        response = await self.service.GenerateVivoxToken(request=request, context=None)

        # assert

        # https://docs.vivox.com/v5/general/unity/15_1_160000/en-us/access-token-guide/access-token-examples/example-login-token.htm
        expected_token = "e30.eyJ2eGkiOjkzMzAwMCwiZiI6InNpcDouYmxpbmRtZWxvbi1BcHBOYW1lLWRldi5qZXJreS5AdGxhLnZpdm94Lm" \
                         "NvbSIsImlzcyI6ImJsaW5kbWVsb24tQXBwTmFtZS1kZXYiLCJ2eGEiOiJsb2dpbiIsImV4cCI6MTYwMDM0OTQwMH0." \
                         "YJwjX0P2Pjk1dzFpIo1fjJM21pphfBwHm8vShJib8ds"
        expected_claims = self.decode_token(expected_token)

        self.assertIsNotNone(response)
        self.assertEqual(
            expected_claims,
            self.decode_token(response.accessToken),
        )

    async def test_generate_vivox_token_join(self) -> None:
        # arrange
        request = GenerateVivoxTokenRequest()
        request.type = GenerateVivoxTokenRequestType.join
        request.username = "jerky"
        request.channelId = "testchannel"
        request.channelType = GenerateVivoxTokenRequestChannelType.nonpositional

        # monkey-patch
        self.service.provider.get_exp = lambda: 1600349400
        self.service.provider.get_vxi = lambda: 444000

        # act
        response = await self.service.GenerateVivoxToken(request=request, context=None)

        # assert

        # https://docs.vivox.com/v5/general/unity/15_1_160000/en-us/access-token-guide/access-token-examples/example-join-token.htm
        expected_token = "e30.eyJ2eGkiOjQ0NDAwMCwiZiI6InNpcDouYmxpbmRtZWxvbi1BcHBOYW1lLWRldi5qZXJreS5AdGxhLnZpdm94Lm" \
                         "NvbSIsImlzcyI6ImJsaW5kbWVsb24tQXBwTmFtZS1kZXYiLCJ2eGEiOiJqb2luIiwidCI6InNpcDpjb25mY3RsLWct" \
                         "YmxpbmRtZWxvbi1BcHBOYW1lLWRldi50ZXN0Y2hhbm5lbEB0bGEudml2b3guY29tIiwiZXhwIjoxNjAwMzQ5NDAwfQ" \
                         ".u7us5eCxOBtuEZuDg1HapEEgxLedLaliIy7gOMfbeko"
        expected_claims = self.decode_token(expected_token)

        self.assertIsNotNone(response)
        self.assertEqual(
            expected_claims,
            self.decode_token(response.accessToken),
        )

    async def test_generate_vivox_token_join_muted(self) -> None:
        # arrange
        request = GenerateVivoxTokenRequest()
        request.type = GenerateVivoxTokenRequestType.join_muted
        request.username = "jerky"
        request.channelId = "testchannel"
        request.channelType = GenerateVivoxTokenRequestChannelType.nonpositional

        # monkey-patch
        self.service.provider.get_exp = lambda: 1600349400
        self.service.provider.get_vxi = lambda: 542680

        # act
        response = await self.service.GenerateVivoxToken(request=request, context=None)

        # assert

        # https://docs.vivox.com/v5/general/unity/15_1_160000/en-us/access-token-guide/access-token-examples/example-join-muted-token.htm
        expected_token = "e30.eyJ2eGkiOjU0MjY4MCwiZiI6InNpcDouYmxpbmRtZWxvbi1BcHBOYW1lLWRldi5qZXJreS5AdGxhLnZpdm94Lm" \
                         "NvbSIsImlzcyI6ImJsaW5kbWVsb24tQXBwTmFtZS1kZXYiLCJ2eGEiOiJqb2luX211dGVkIiwidCI6InNpcDpjb25m" \
                         "Y3RsLWctYmxpbmRtZWxvbi1BcHBOYW1lLWRldi50ZXN0Y2hhbm5lbEB0bGEudml2b3guY29tIiwiZXhwIjoxNjAwMz" \
                         "Q5NDAwfQ.N6sZL3F3e-p2KLQlMweXnbGNzE7Qc91rn_uqCEtRjsc"
        expected_claims = self.decode_token(expected_token)

        self.assertIsNotNone(response)
        self.assertEqual(
            expected_claims,
            self.decode_token(response.accessToken),
        )

    async def test_generate_vivox_token_kick(self) -> None:
        # arrange
        request = GenerateVivoxTokenRequest()
        request.type = GenerateVivoxTokenRequestType.kick
        request.username = "beef"
        request.channelId = "testchannel"
        request.channelType = GenerateVivoxTokenRequestChannelType.nonpositional
        request.targetUsername = "jerky"

        # monkey-patch
        self.service.provider.get_exp = lambda: 1600349400
        self.service.provider.get_vxi = lambda: 665000

        # act
        response = await self.service.GenerateVivoxToken(request=request, context=None)

        # assert

        # https://docs.vivox.com/v5/general/unity/15_1_160000/en-us/access-token-guide/access-token-examples/example-kick-token.htm
        expected_token = "e30.eyJ2eGkiOjY2NTAwMCwic3ViIjoic2lwOi5ibGluZG1lbG9uLUFwcE5hbWUtZGV2Lmplcmt5LkB0bGEudml2b3" \
                         "guY29tIiwiZiI6InNpcDouYmxpbmRtZWxvbi1BcHBOYW1lLWRldi5iZWVmLkB0bGEudml2b3guY29tIiwiaXNzIjoi" \
                         "YmxpbmRtZWxvbi1BcHBOYW1lLWRldiIsInZ4YSI6ImtpY2siLCJ0Ijoic2lwOmNvbmZjdGwtZy1ibGluZG1lbG9uLU" \
                         "FwcE5hbWUtZGV2LnRlc3RjaGFubmVsQHRsYS52aXZveC5jb20iLCJleHAiOjE2MDAzNDk0MDB9.kKnWD3smth6KUuR" \
                         "aY11O-yqAbXy2L2wDZeIoDK_098c"
        expected_claims = self.decode_token(expected_token)

        self.assertIsNotNone(response)
        self.assertEqual(
            expected_claims,
            self.decode_token(response.accessToken),
        )