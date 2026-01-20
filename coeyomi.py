import asyncio
import logging
import os
import re
import subprocess
from typing import List, Union

import discord
import jaconv
from discord import (
    ClientException,
    FFmpegPCMAudio,
    Guild,
    Member,
    Message,
    Reaction,
    User,
    VoiceState,
)
from discord.ext import tasks
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
bot = Bot(intents=discord.Intents.all())


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
            print(f"{cfg['default']['startup_timeout'] * i}秒後に再試行します...")
            await asyncio.sleep(cfg["default"]["startup_timeout"] * i)
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
    name="setdict",
    description="読み上げ辞書を追加します(ワード、読み、アクセント)",
)
async def setdict(
    ctx: discord.ApplicationContext,
    word: str = discord.Option(
        str,
        description="ワード",
    ),
    yomi: str = discord.Option(
        str,
        description="読み",
    ),
    accent: int = discord.Option(
        int,
        default=0,
        description="アクセント",
    ),
):
    if accent > len(yomi) or 0 > len(yomi):
        await ctx.response.send_message(
            "アクセントの値が不正です!",
            delete_after=5,
        )
        return
    clean_word = await fnc.cleanup_message(word)
    clean_yomi = await fnc.cleanup_message(yomi)
    if clean_word == "" or clean_yomi == "":
        await ctx.response.send_message(
            "利用できない文字列によりワードまたは読みが空になりました!",
            delete_after=5,
        )
        return
    try:
        dict_table = sql.getSingleDictSettings(ctx.user, clean_word)
        dict_table.yomi = clean_yomi
        dict_table.accent = accent
        sql.session.commit()
        await ctx.response.send_message(
            f"ワード:{word}、読み:{yomi}、アクセント:{accent}に設定しました!",
            delete_after=5,
        )
    except Exception as e:
        print(e)
        sql.session.rollback()
        await ctx.response.send_message(
            "設定の保存に失敗しました。管理者にお問い合わせください。", delete_after=5
        )


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
            "設定の保存に失敗しました。管理者にお問い合わせください。", delete_after=5
        )


@bot.slash_command(name="reset", description="指定された設定をリセットします")
async def reset(
    ctx: discord.ApplicationContext,
    target: str = discord.Option(
        str,
        choices=["character", "advanced", "dict"],
        description="リセットする項目",
    ),
    word: str = discord.Option(
        str,
        description="削除するワードを指定します。(辞書を削除する場合にのみ利用可能)",
        default="",
    ),
):
    # TODO:新しい列を作成せずリセットできるようにする
    try:
        match target:
            case "character":
                user_table = sql.getUserSettings(ctx.user)
                user_table.character = None
                user_table.style = None
            case "advanced":
                user_table = sql.getUserSettings(ctx.user)
                user_table.pitchScale = None
                user_table.intonationScale = None
                user_table.processingAlgorithm = None
            case "dict":
                dict_table = sql.getSingleDictSettings(ctx.user, word)
                if dict_table.yomi is None:
                    await ctx.response.send_message(
                        "指定されたワードが辞書に見つかりませんでした!", delete_after=5
                    )
                    sql.session.delete(dict_table)
                    return
                sql.session.delete(dict_table)

        sql.session.commit()
        await ctx.response.send_message(
            f"{target}設定をリセットしました!", delete_after=5
        )
    except Exception:
        sql.session.rollback()
        await ctx.response.send_message(
            "設定の保存に失敗しました。管理者にお問い合わせください。", delete_after=5
        )


@bot.slash_command(
    name="copysettings", description="他のサーバーから設定をインポートします"
)
async def copysettings(
    ctx: discord.ApplicationContext,
    guild_id: int = discord.Option(description="インポート元のサーバーID"),
):
    try:
        if ctx.guild.id == guild_id:
            await ctx.response.send_message(
                "同一のサーバーへのインポートです!", delete_after=5
            )
        elif sql.isExistSettings(ctx.user, guild_id):
            old_user_table = sql.getUserSettings(ctx.user, guild_id)
            new_user_table = sql.getUserSettings(ctx.user)
            new_user_table.character = old_user_table.character
            new_user_table.style = old_user_table.style
            new_user_table.pitchScale = old_user_table.pitchScale
            new_user_table.intonationScale = old_user_table.intonationScale
            new_user_table.processingAlgorithm = old_user_table.processingAlgorithm
            sql.session.commit()
            await ctx.response.send_message("設定をインポートしました!", delete_after=5)
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
            g.voiceChatDict[ctx.guild_id] = VoiceChat(
                voiceChannel=vc, calledChannel=ctx.channel, voiceQueue=[]
            )
            await ctx.followup.send(
                embed=discord.Embed(
                    title=f"{channel.name}に参加しました",
                    description="このボットを利用する場合、[COEIROINKの規約](https://coeiroink.com/terms)に同意したこととみなします。\n※ 音声利用の際は「COEIROINK」と「合成音声名」が含まれるクレジット表記が必須です。",
                    color=discord.Colour.blue(),
                ),
                delete_after=5,
            )
        else:
            await ctx.followup.send(
                "既にボイスチャンネルに参加しています!\n強制的に切断した場合はしばらく時間を置いてからお試しください。",
                delete_after=5,
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
    await ctx.defer()
    if ctx.guild_id in g.voiceChatDict.keys():
        vc = g.voiceChatDict[ctx.guild_id]["voiceChannel"]
        await vc.disconnect()
        del g.voiceChatDict[ctx.guild_id]
        await ctx.followup.send("ボイスチャンネルから切断しました", delete_after=5)
    elif ctx.guild.get_member(bot.user.id).voice.channel is not None:
        vc = await ctx.guild.get_member(bot.user.id).voice.channel.connect()
        await vc.disconnect()
        await ctx.followup.send("ボイスチャンネルから切断しました", delete_after=5)
    else:
        await ctx.followup.send("ボイスチャンネルに参加していません！", delete_after=5)


@bot.event
async def on_guild_join(guild: Guild):
    if (
        guild.system_channel
        and guild.system_channel.permissions_for(guild.me).send_messages
    ):
        await guild.system_channel.send(
            embed=discord.Embed(
                title="声詠みちゃんをご利用いただきありがとうございます!",
                description="バグ報告は[github](https://github.com/creeper-0910/COEYOMI/issues)、または[Twitter](https://x.com/Riku_2004)までお願いいたします!\nこのボットを利用する場合、[COEIROINKの規約](https://coeiroink.com/terms)に同意したこととみなします。\n※ 音声利用の際は「COEIROINK」と「合成音声名」が含まれるクレジット表記が必須です。\nまた、動画配信サービス等で読み上げ機能をご利用頂く場合は、\n[「COEIROINKを用いたコンテンツの配信・切り抜き許可について」](https://coeiroink.com/terms#optional-terms)に基づき、Bot名の記載をお願いいたします。",
                color=discord.Colour.blue(),
            )
        )
        return

    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            await channel.send(
                embed=discord.Embed(
                    title="声詠みちゃんをご利用いただきありがとうございます!",
                    description="バグ報告は[github](https://github.com/creeper-0910/COEYOMI/issues)、または[Twitter](https://x.com/Riku_2004)までお願いいたします!\nこのボットを利用する場合、[COEIROINKの規約](https://coeiroink.com/terms)に同意したこととみなします。\n※ 音声利用の際は「COEIROINK」と「合成音声名」が含まれるクレジット表記が必須です。\nまた、動画配信サービス等で読み上げ機能をご利用頂く場合は、\n[「COEIROINKを用いたコンテンツの配信・切り抜き許可について」](https://coeiroink.com/terms#optional-terms)に基づき、Bot名の記載をお願いいたします。",
                    color=discord.Colour.blue(),
                )
            )
            break


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
        selectedName = (
            reaction.message.embeds[0].fields[g.menu_emojis.index(reaction.emoji)].name
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
        g.styleDict[msg.id] = PageAndUuid(
            paginator=paginator, uuid=selectedUuid, name=selectedName
        )
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
        user_table.character = g.styleDict[reaction.message.id]["uuid"]
        user_table.style = (
            reaction.message.embeds[0].fields[g.menu_emojis.index(reaction.emoji)].value
        )
        try:
            sql.session.commit()
            msg = await reaction.message.reply(
                f"{user.mention}",
                embed=discord.Embed(
                    title="音源の変更に成功しました!",
                    description=f"COEIROINK: {g.styleDict[reaction.message.id]['name'].split('-', 1)[1].strip()}",
                    color=discord.Colour.blue(),
                ),
            )
        except Exception as e:
            sql.session.rollback()
            msg = await reaction.message.reply(
                f"{user.mention}\n設定の保存に失敗しました。管理者にお問い合わせください。"
            )
            print(e)
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
        message_text = message.content
        user_table = sql.getUserSettings(message.author)
        dicts_table = sql.getAllDictSettings(message.author)
        character = user_table.character
        style = user_table.style
        pitch = user_table.pitchScale
        intonation = user_table.intonationScale
        algorithm = user_table.processingAlgorithm
        # メッセージの加工
        if len(message.mentions) != 0:
            for mention in reversed(message.mentions):
                message_text = f"{mention.display_name}さん {message_text}"

        message_text = await fnc.cleanup_message(message_text)

        # ファイルの種類と数をカウント
        if len(message.attachments) != 0:
            attach_count = {}
            for i in range(len(message.attachments)):
                if "image" in message.attachments[i].content_type:
                    if(message.attachments[i].filename.startswith("SPOILER_")):
                        attach_count["spoiler_image"] = attach_count.get("spoiler_image", 0) + 1
                    else:
                        attach_count["image"] = attach_count.get("image", 0) + 1
                elif "video" in message.attachments[i].content_type:
                    attach_count["video"] = attach_count.get("video", 0) + 1
                elif "audio" in message.attachments[i].content_type:
                    attach_count["audio"] = attach_count.get("audio", 0) + 1
                else:
                    attach_count["other"] = attach_count.get("other", 0) + 1

            if attach_count.get("spoiler_image", None) is not None:
                message_text = (
                    str(attach_count["spoiler_image"]) + "件の隠し画像ファイル " + message_text
                )
            if attach_count.get("image", None) is not None:
                message_text = (
                    str(attach_count["image"]) + "件の画像ファイル " + message_text
                )
            if attach_count.get("video", None) is not None:
                message_text = (
                    str(attach_count["video"]) + "件の動画ファイル " + message_text
                )
            if attach_count.get("audio", None) is not None:
                message_text = (
                    str(attach_count["audio"]) + "件の音声ファイル " + message_text
                )
            if attach_count.get("other", None) is not None:
                message_text = (
                    str(attach_count["other"]) + "件のファイル " + message_text
                )

        # リンク数をカウントし、リンクは削除する
        linkcount = len(
            re.findall(
                r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
                message_text,
            )
        )
        if linkcount != 0:
            message_text = re.sub(
                r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
                "",
                message_text,
            )
            message_text = str(linkcount) + "件のリンク " + message_text

        if message_text:
            # 話者のフォールバック処理
            if not any(s["speakerUuid"] == character for s in g.speakerList):
                if any(
                    s["speakerUuid"] == cfg["default"]["defaultCharacter"]
                    for s in g.speakerList
                ):
                    character = cfg["default"]["defaultCharacter"]
                    style = cfg["default"]["defaultStyle"]
                else:
                    character = g.speakerList[0]["speakerUuid"]
                    style = g.speakerList[0]["styles"][0]["styleId"]
            # 辞書データのロード
            await api.setdict(
                dicts=[
                    {
                        "word": jaconv.hira2kata(
                            jaconv.h2z(dt.word, kana=True, ascii=True, digit=True)
                        ),
                        "yomi": jaconv.hira2kata(
                            jaconv.h2z(dt.yomi, kana=True, ascii=True, digit=True)
                        ),
                        "accent": dt.accent,
                        "numMoras": len(dt.yomi),
                    }
                    for dt in dicts_table
                ]
            )
            # 音声データの生成
            audio_data = await api.genvoice(
                message_text,
                character,
                style,
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
        vc = g.voiceChatDict[member.guild.id]["voiceChannel"]
        if member == bot.user:
            # ボット自身が切断された場合にキューを削除
            del g.voiceChatDict[member.guild.id]
            await asyncio.sleep(5)
            for queue in vq:
                os.remove(queue)
        elif (
            member.guild.voice_client.channel is not None
            and len(member.guild.voice_client.channel.members) == 1
        ):
            del g.voiceChatDict[member.guild.id]
            await vc.disconnect()
            await asyncio.sleep(5)
            for queue in vq:
                os.remove(queue)


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
