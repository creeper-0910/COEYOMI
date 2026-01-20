import re
import discord
from discord.ext.pages import Page

from coeyomi_class import CustomPaginator


class COEYOMI_FUNC:
    def __init__(self, g, cfg):
        self.g = g
        self.cfg = cfg

    async def update_page_reaction(self, msg):
        await msg.clear_reactions()
        for i in range(len(msg.embeds[0].fields)):
            await msg.add_reaction(self.g.menu_emojis[i])

    async def create_pages(
        self, values, nameKey: str, valueKey: str, owner_id: int, inline=True
    ):
        pages = []
        split = int(self.cfg["default"]["split"])
        for i in range(0, len(values), split):
            embed = discord.Embed(title="キャラクター設定")
            for j, value in enumerate(values[i : i + split]):
                embed.add_field(
                    name=" - ".join([self.g.menu_emojis[j], value[nameKey]]),
                    value=value[valueKey],
                    inline=inline,
                )
            pages.append(Page(embeds=[embed]))
        return CustomPaginator(pages=pages, owner_id=owner_id, g=self.g, fnc=self)

    async def cleanup_message(self, message_text:str):
        message_text = re.sub(r"<\S{1,}>", "", message_text)
        message_text = re.sub(r"\n", " ", message_text)
        message_text = re.sub("'", "", message_text)
        message_text = re.sub(r"\x1B\[[0-?]*[ -/]*[@-~]","", message_text)

        for regexp_data in self.cfg["default"]["regexp"]:
            if regexp_data["exp"] != "":
                regexp = re.compile(regexp_data["exp"])
                message_text = re.sub(regexp, regexp_data["replace"], message_text)
        return message_text