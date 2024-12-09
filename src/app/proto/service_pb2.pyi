from google.api import annotations_pb2 as _annotations_pb2
from protoc_gen_openapiv2.options import annotations_pb2 as _annotations_pb2_1
import permission_pb2 as _permission_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor
echo: GenerateVivoxTokenRequestChannelType
generatevivoxtokenrequest_channeltype_unknown: GenerateVivoxTokenRequestChannelType
generatevivoxtokenrequest_type_unknown: GenerateVivoxTokenRequestType
join: GenerateVivoxTokenRequestType
join_muted: GenerateVivoxTokenRequestType
kick: GenerateVivoxTokenRequestType
login: GenerateVivoxTokenRequestType
nonpositional: GenerateVivoxTokenRequestChannelType
positional: GenerateVivoxTokenRequestChannelType

class GenerateVivoxTokenRequest(_message.Message):
    __slots__ = ["channelId", "channelType", "targetUsername", "type", "username"]
    CHANNELID_FIELD_NUMBER: _ClassVar[int]
    CHANNELTYPE_FIELD_NUMBER: _ClassVar[int]
    TARGETUSERNAME_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    channelId: str
    channelType: GenerateVivoxTokenRequestChannelType
    targetUsername: str
    type: GenerateVivoxTokenRequestType
    username: str
    def __init__(self, type: _Optional[_Union[GenerateVivoxTokenRequestType, str]] = ..., username: _Optional[str] = ..., channelId: _Optional[str] = ..., channelType: _Optional[_Union[GenerateVivoxTokenRequestChannelType, str]] = ..., targetUsername: _Optional[str] = ...) -> None: ...

class GenerateVivoxTokenResponse(_message.Message):
    __slots__ = ["accessToken", "uri"]
    ACCESSTOKEN_FIELD_NUMBER: _ClassVar[int]
    URI_FIELD_NUMBER: _ClassVar[int]
    accessToken: str
    uri: str
    def __init__(self, accessToken: _Optional[str] = ..., uri: _Optional[str] = ...) -> None: ...

class GenerateVivoxTokenRequestType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []

class GenerateVivoxTokenRequestChannelType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = []
