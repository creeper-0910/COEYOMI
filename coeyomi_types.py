from typing import List, TypedDict

import discord

from coeyomi_class import CustomPaginator


class Style(TypedDict):
    styleName: str
    styleId: int
    base64Icon: str
    base64Portrait: str


class Speaker(TypedDict):
    speakerName: str
    speakerUuid: str
    styles: List[Style]
    version: str
    base64Portrait: str


class VoiceChat(TypedDict):
    voiceChannel: discord.voice_client.VoiceClient
    calledChannel: discord.channel.TextChannel
    voiceQueue: List[str]


class PageAndUuid(TypedDict):
    paginator: CustomPaginator
    uuid: str
