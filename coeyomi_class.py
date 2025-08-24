import discord
from discord.ext.pages import Paginator


# Paginatorを継承したクラス
# 利用可能な引数は__init__より確認可能
# owner_id: コマンドを呼び出したユーザーのID
# g: グローバル変数
# fnc: 共通関数
class CustomPaginator(Paginator):
    def __init__(self, *, owner_id: int, g, fnc, **kwargs):
        super().__init__(**kwargs)
        self.owner_id = owner_id
        self.g = g
        self.fnc = fnc

    async def on_timeout(self):
        if self.message.id in self.g.charaDict.keys():
            del self.g.charaDict[self.message.id]
        await self.message.delete()
        # return await super().on_timeout()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "この操作はコマンドを実行したユーザーのみが利用できます。",
                ephemeral=True,
            )
            return False
        return True

    async def goto_page(self, **kwargs):
        await super().goto_page(**kwargs)
        await self.fnc.update_page_reaction(self.message)
