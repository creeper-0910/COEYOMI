from typing import Dict, List

from coeyomi_class import CustomPaginator
from coeyomi_types import PageAndUuid, Speaker, VoiceChat


class GV:
    charaDict: Dict[int, CustomPaginator] = {}
    styleDict: Dict[int, PageAndUuid] = {}
    speakerList: List[Speaker] = []
    voiceChatDict: Dict[int, VoiceChat] = {}
    coeiro_process = None
    menu_emojis = [
        "\N{REGIONAL INDICATOR SYMBOL LETTER A}",
        "\N{REGIONAL INDICATOR SYMBOL LETTER B}",
        "\N{REGIONAL INDICATOR SYMBOL LETTER C}",
        "\N{REGIONAL INDICATOR SYMBOL LETTER D}",
        "\N{REGIONAL INDICATOR SYMBOL LETTER E}",
        "\N{REGIONAL INDICATOR SYMBOL LETTER F}",
        "\N{REGIONAL INDICATOR SYMBOL LETTER G}",
        "\N{REGIONAL INDICATOR SYMBOL LETTER H}",
        "\N{REGIONAL INDICATOR SYMBOL LETTER I}",
        "\N{REGIONAL INDICATOR SYMBOL LETTER J}",
        "\N{REGIONAL INDICATOR SYMBOL LETTER K}",
        "\N{REGIONAL INDICATOR SYMBOL LETTER L}",
        "\N{REGIONAL INDICATOR SYMBOL LETTER M}",
        "\N{REGIONAL INDICATOR SYMBOL LETTER N}",
        "\N{REGIONAL INDICATOR SYMBOL LETTER O}",
        "\N{REGIONAL INDICATOR SYMBOL LETTER P}",
        "\N{REGIONAL INDICATOR SYMBOL LETTER Q}",
        "\N{REGIONAL INDICATOR SYMBOL LETTER R}",
        "\N{REGIONAL INDICATOR SYMBOL LETTER S}",
        "\N{REGIONAL INDICATOR SYMBOL LETTER T}",
    ]
