import asyncio
import logging
import os
import subprocess
from typing import List, Union

import discord
from discord import (
    ClientException,
    FFmpegPCMAudio,
    Member,
    Message,
    Reaction,
    User,
    VoiceState,
)
from discord.ext import commands, tasks
from discord.ext.commands import Bot
from dynaconf import Dynaconf
from nanoid import generate
from rich.logging import RichHandler

from coeyomi_api import COEIROINK_API
from coeyomi_class import CustomPaginator
from coeyomi_db import SQL
from coeyomi_function import COEYOMI_FUNC
from coeyomi_types import PageAndUuid, Style, VoiceChat
from global_variable import GV

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(markup=True, rich_tracebacks=True)],
)

print = logging.info

# 環境変数のセットアップ
cfg = Dynaconf(settings_files=["config.toml"])

api = COEIROINK_API(api_url=cfg["default"]["coeiroink_url"])
g = GV()
fnc = COEYOMI_FUNC(g, cfg)
sql = SQL(cfg["default"]["database"])
sql.createTable()
bot = Bot(owner_ids=cfg["default"]["owner_id"], intents=discord.Intents.all())


@bot.event
async def on_ready():
    status = await api.heartbeat()
    if status != "start":
        g.coeiro_process = subprocess.Popen(
            cfg["default"]["coeiroink_path"], shell=True
        )
        print("COEIROINKの起動を待機しています...")
        for i in range(1, 6, 1):
            status = await api.heartbeat()
            if status == "start":
                break
            elif i >= 5:
                print(
                    "COEIROINKの起動が時間内に完了しませんでした!\n設定ファイルからタイムアウト時間の延長を行うか、ファイルを確認してください!"
                )
                bot.loop.stop()
                await asyncio.sleep(5)
                return
            print(f"{cfg["default"]["startup_timeout"]*i}秒後に再試行します...")
            await asyncio.sleep(cfg["default"]["startup_timeout"]*i)
    print(cfg["default"]["coeiroink_path"])
    g.speakerList = await api.getspeaker()
    print(f"{bot.user}としてログインしました!")
    print(await bot.application_info())
    if not playQueue.is_running():
        playQueue.start()


@bot.event
async def close():
    if g.coeiro_process is not None and g.coeiro_process.poll() is not None:
        g.coeiro_process.kill()
        g.coeiro_process.wait()
    sql.session.close()
    for voiceGuild in g.voiceChatDict.keys():
        vc = g.voiceChatDict[voiceGuild]["voiceChannel"]
        await vc.disconnect()
    g.voiceChatDict.clear()


@bot.slash_command(name="chara", description="使用するキャラクターを設定できます")
async def chara(ctx: discord.ApplicationContext):
    await ctx.defer()
    paginator: CustomPaginator = await fnc.create_pages(
        g.speakerList, "speakerName", "speakerUuid", ctx.author.id, False
    )
    msg = await paginator.respond(ctx.interaction)
    g.charaDict[msg.id] = paginator
    await fnc.update_page_reaction(msg)


@bot.slash_command(
    name="advanced",
    description="高度な設定を行います(声の高さ、抑揚、加工手法)",
)
async def advanced(
    ctx: discord.ApplicationContext,
    pitchscale: float = discord.Option(
        float,
        min_value=-0.15,
        max_value=0.15,
        default=0.00,
        description="声の高さ(-0.15~0.15)",
    ),
    intonationscale: float = discord.Option(
        float,
        min_value=0.00,
        max_value=2.00,
        default=1.00,
        description="抑揚(0.00~2.00)",
    ),
    processingalgorithm: str = discord.Option(
        str,
        choices=["td-psola", "world", "resampling"],
        default="td-psola",
        description="加工手法",
    ),
):
    user_table = sql.getUserSettings(ctx.user)
    try:
        user_table.pitchScale = pitchscale
        user_table.intonationScale = intonationscale
        user_table.processingAlgorithm = processingalgorithm
        sql.session.commit()
        await ctx.response.send_message(
            f"声の高さ:{pitchscale}、抑揚:{intonationscale}、加工手法:{processingalgorithm}に設定しました!",
            delete_after=5,
        )
    except Exception:
        sql.session.rollback()
        await ctx.response.send_message(
            "設定の保存に失敗しました。管理者にお問い合わせください。"
        )


@bot.slash_command(name="reset", description="指定された設定をリセットします")
async def reset(
    ctx: discord.ApplicationContext,
    target: str = discord.Option(
        str,
        choices=["character", "advanced"],
        description="リセットする項目",
    ),
):
    user_table = sql.getUserSettings(ctx.user)
    try:
        match target:
            case "character":
                user_table.character = None
                user_table.style = None
            case "advanced":
                user_table.pitchScale = None
                user_table.intonationScale = None
                user_table.processingAlgorithm = None
        sql.session.commit()
        await ctx.response.send_message(
            f"{target}設定をリセットしました!", delete_after=5
        )
    except Exception:
        sql.session.rollback()
        await ctx.response.send_message(
            "設定の保存に失敗しました。管理者にお問い合わせください。"
        )

@bot.slash_command(name="copysettings", description="他のサーバーから設定をインポートします")
async def copysettings(
    ctx: discord.ApplicationContext,
    guild_id: int = discord.Option(
        description="インポート元のサーバーID"
    ),
):
    try:
        if ctx.guild.id == guild_id:
            await ctx.response.send_message(
                "同一のサーバーへのインポートです!", delete_after=5
            )
        elif sql.isExistSettings(ctx.user,guild_id):
            old_user_table = sql.getUserSettings(ctx.user,guild_id)
            new_user_table = sql.getUserSettings(ctx.user)
            new_user_table.character = old_user_table.character
            new_user_table.style = old_user_table.style
            new_user_table.pitchScale = old_user_table.pitchScale
            new_user_table.intonationScale = old_user_table.intonationScale
            new_user_table.processingAlgorithm = old_user_table.processingAlgorithm
            sql.session.commit()
            await ctx.response.send_message(
                "設定をインポートしました!", delete_after=5
            )
        else:
            await ctx.response.send_message(
                "指定されたサーバーIDが見つかりませんでした", delete_after=5
            )
    except Exception:
        sql.session.rollback()
        await ctx.response.send_message(
            "設定の保存に失敗しました。管理者にお問い合わせください。", delete_after=5
        )

@bot.slash_command(name="join", description="声詠みちゃんをボイスチャットに接続します")
async def join(ctx: discord.ApplicationContext):
    await ctx.defer()
    if ctx.user.voice:
        if ctx.guild.voice_client is None:
            channel = ctx.user.voice.channel
            vc = await channel.connect()
            print(type(vc))
            print(type(ctx.channel))
            g.voiceChatDict[ctx.guild_id] = VoiceChat(
                voiceChannel=vc, calledChannel=ctx.channel, voiceQueue=[]
            )
            await ctx.followup.send(f"{channel.name}に参加しました", delete_after=5)
        else:
            await ctx.followup.send(
                "既にボイスチャンネルに参加しています!\n強制的に切断した場合はしばらく時間を置いてからお試しください。", delete_after=5
            )
    else:
        await ctx.followup.send(
            "ボイスチャットに参加してからこのコマンドを実行してください!",
            delete_after=5,
        )


@bot.slash_command(
    name="leave",
    description="声詠みちゃんをボイスチャットから切断します",
    delete_after=5,
)
async def leave(ctx: discord.ApplicationContext):
    print(g.voiceChatDict)
    await ctx.defer()
    if ctx.guild_id in g.voiceChatDict.keys():
            vc = g.voiceChatDict[ctx.guild_id]["voiceChannel"]
            await vc.disconnect()
            await ctx.followup.send("ボイスチャンネルから切断しました", delete_after=5)
    else:
        await ctx.followup.send("ボイスチャンネルに参加していません！", delete_after=5)

@bot.event
async def on_message_delete(message: Message):
    if message.author != bot.user:
        return
    # キャラクター設定のクリーンアップ
    if message.id in g.charaDict.keys():
        g.charaDict[message.id].stop()
        del g.charaDict[message.id]
    # スタイル設定のクリーンアップ
    if message.id in g.styleDict.keys():
        g.styleDict[message.id]["paginator"].stop()
        del g.styleDict[message.id]


@bot.event
async def on_reaction_add(reaction: Reaction, user: Union[Member, User]):
    # 自身の場合は処理をしない
    if user == bot.user:
        return
    user_table = sql.getUserSettings(user)
    # キャラクター設定のメッセージIDが記録されているか
    if reaction.message.id in g.charaDict.keys():
        charaDict: CustomPaginator = g.charaDict[reaction.message.id]
        style: List[Style] = {}
        # コマンドを実行したユーザーでない場合は処理をしない
        if charaDict.owner_id != user.id:
            await reaction.remove(user)
            msg = await reaction.message.reply(
                f"{user.mention}\nこのコマンドは複数人で使用できません。\n`/chara`で設定メニューを表示できます！"
            )
            await msg.delete(delay=5)
            return
        selectedUuid = (
            reaction.message.embeds[0].fields[g.menu_emojis.index(reaction.emoji)].value
        )
        for speaker in g.speakerList:
            if speaker["speakerUuid"] == selectedUuid:
                style = speaker["styles"]
                break
        paginator: CustomPaginator = await fnc.create_pages(
            style, "styleName", "styleId", charaDict.owner_id, False
        )
        await reaction.message.delete()
        msg = await paginator.send(await Bot.get_context(bot, reaction.message))
        g.styleDict[msg.id] = PageAndUuid(paginator=paginator, uuid=selectedUuid)
        await fnc.update_page_reaction(msg)
    # キャラクター設定のメッセージIDが記録されているか
    elif reaction.message.id in g.styleDict.keys():
        styleDict: CustomPaginator = g.styleDict[reaction.message.id]["paginator"]
        # コマンドを実行したユーザーでない場合は処理をしない
        if styleDict.owner_id != user.id:
            await reaction.remove(user)
            msg = await reaction.message.reply(
                f"{user.mention}\nこのコマンドは複数人で使用できません。\n`/chara`で設定メニューを表示できます！"
            )
            await msg.delete(delay=5)
            return
        print(g.styleDict[reaction.message.id]["uuid"])
        print(
            reaction.message.embeds[0].fields[g.menu_emojis.index(reaction.emoji)].value
        )
        user_table.character = g.styleDict[reaction.message.id]["uuid"]
        user_table.style = (
            reaction.message.embeds[0].fields[g.menu_emojis.index(reaction.emoji)].value
        )
        try:
            sql.session.commit()
            msg = await reaction.message.reply(
                f"{user.mention}\n音源の変更に成功しました!"
            )
        except Exception:
            sql.session.rollback()
            msg = await reaction.message.reply(
                f"{user.mention}\n設定の保存に失敗しました。管理者にお問い合わせください。"
            )
        finally:
            await msg.delete(delay=5)
            await reaction.message.delete()


@bot.event
async def on_message(message: Message):
    if message.author == bot.user or message.author.bot:
        return
    if message.guild.id in g.voiceChatDict.keys():
        if g.voiceChatDict[message.guild.id]["calledChannel"] != message.channel:
            return
        vq = g.voiceChatDict[message.guild.id]["voiceQueue"]
        user_table = sql.getUserSettings(message.author)
        character = user_table.character
        style = user_table.style
        pitch = user_table.pitchScale
        intonation = user_table.intonationScale
        algorithm = user_table.processingAlgorithm
        isExistSpeaker = False

        for speaker in g.speakerList:
            if speaker["speakerUuid"] == character:
                isExistSpeaker = True
                break
        if not isExistSpeaker:
            character = None
            style = None

        audio_data = await api.genvoice(
            message.content,
            character or cfg["default"]["defaultCharacter"],
            style or cfg["default"]["defaultStyle"],
            pitch or 0,
            intonation or 1,
            algorithm or "td-psola",
        )
        audio_name = f"{generate(size=16)}.wav"
        with open(audio_name, "wb") as f:
            f.write(audio_data)
        vq.append(audio_name)


@bot.event
async def on_voice_state_update(member: Member, before: VoiceState, after: VoiceState):
    if member.guild.id in g.voiceChatDict.keys() and after.channel is None:
        vq = g.voiceChatDict[member.guild.id]["voiceQueue"]
        if member == bot.user:
            await asyncio.sleep(5)
            for queue in vq:
                os.remove(queue)
            del g.voiceChatDict[member.guild.id]
        elif (
            member.guild.voice_client.channel is not None
            and len(member.guild.voice_client.channel.members) == 1
        ):
            vc = g.voiceChatDict[member.guild.id]["voiceChannel"]
            await vc.disconnect()
            await asyncio.sleep(5)
            for queue in vq:
                os.remove(queue)
            del g.voiceChatDict[member.guild.id]


@tasks.loop(seconds=2)
async def playQueue():
    for vqGuild in g.voiceChatDict.keys():
        vc = g.voiceChatDict[vqGuild]["voiceChannel"]
        vq = g.voiceChatDict[vqGuild]["voiceQueue"]
        if vq and not vc.is_playing():
            try:
                await vc.play(
                    FFmpegPCMAudio(
                        vq[0],
                        executable=cfg["default"]["ffmepg_path"],
                        options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                    ),
                    wait_finish=True,
                )
                os.remove(vq[0])
                del vq[0]
            except ClientException:
                pass

bot.run(cfg["default"]["bot_token"])