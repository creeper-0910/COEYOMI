import configparser
import os
import re

import discord
from discord import Client, FFmpegPCMAudio, Intents, Interaction, app_commands
from discord.app_commands import CommandTree
from discord.ui import Select, View

import api
import config as cfg

user_conf = configparser.ConfigParser()

def matchindex(mention_list,id):
    for i in range(len(mention_list)):
        if  str(id) in str(mention_list[i]):
            return i
    return None

# ここからBotのコード

class Settings(app_commands.Group):
    def __init__(self, name: str):
        super().__init__(name=name)

    @app_commands.command()
    async def chara(self,interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        if not (interaction.guild.id in user_conf):
            user_conf[str(interaction.guild.id)] = {}
        cfg.speaker = api.getspeaker()
        view = SelectChara()
        for i in range(len(cfg.speaker)):
            view.selectMenu.add_option(
                label=cfg.speaker[i]["speakerName"],
                value=i,
                description=cfg.speaker[i]["speakerUuid"],
            )

        cfg.delete_msg = await interaction.followup.send("キャラクターを選択してください", view=view, ephemeral=True)
    @app_commands.command()
    async def list(self,interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        cfg.speaker = api.getspeaker()
        embed = discord.Embed(title="キャラクター一覧")
        for i in range(len(cfg.speaker)):
            style_list = ""
            for j in range(len(cfg.speaker[i]["styles"])):
                style_list = style_list + cfg.speaker[i]["styles"][j]["styleName"] + "\n"
            embed.add_field(name=cfg.speaker[i]["speakerName"],value=style_list,inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)


class MyClient(Client):
    def __init__(self, intents: Intents) -> None:
        super().__init__(intents=intents)
        self.tree = CommandTree(self)
        self.tree.add_command(Settings("settings"))

    async def setup_hook(self) -> None:
        await self.tree.sync()

    async def on_ready(self):
        user_conf.read(cfg.user_file)
        print(f'Logged in as {client.user.name}')

    async def close(self):
        for vc in cfg.in_voice.values():
            await vc.disconnect()
        with open(cfg.user_file, 'w') as user_data:
            user_conf.write(user_data)
        print(f'Goodbye')

intents = Intents.all()
client = MyClient(intents=intents)

class SelectStyle(View):
    @discord.ui.select(
        cls=Select,
        placeholder="スタイルを選択"
    )
    async def selectMenu(self, interaction: Interaction, select: Select):
        await cfg.delete_msg.delete()
        await interaction.response.defer(ephemeral=True)
        user_conf[str(interaction.guild.id)][str(interaction.user.id)+"-id"] = select.values[0]


class SelectChara(View):
    @discord.ui.select(
        cls=Select,
        placeholder="キャラクターを選択"
    )
    async def selectMenu(self, interaction: Interaction, select: Select):
        await cfg.delete_msg.delete()
        await interaction.response.defer(ephemeral=True)
        view = SelectStyle()
        user_conf[str(interaction.guild.id)][str(interaction.user.id)+"-chara"] = cfg.speaker[int(select.values[0])]["speakerUuid"]
        for i in range(len(cfg.speaker[int(select.values[0])]["styles"])):
            view.selectMenu.add_option(
                label=cfg.speaker[int(select.values[0])]["styles"][i]["styleName"],
                value=cfg.speaker[int(select.values[0])]["styles"][i]["styleId"],
                description=str(cfg.speaker[int(select.values[0])]["styles"][i]["styleId"]),
            )

        cfg.delete_msg = await interaction.followup.send("スタイルを選択してください", view=view, ephemeral=True)

@client.tree.command()
async def join(interaction: Interaction):
    if interaction.user.voice and interaction.user.voice.channel:
        channel = interaction.user.voice.channel
        if interaction.guild.voice_client is None:
            vc = await channel.connect()
            await interaction.response.send_message(f'{channel.name}に参加しました')
            cfg.in_voice[interaction.guild.id] = vc
            cfg.call_channel[interaction.guild.id] = interaction.channel
        else:
            await interaction.response.send_message('既にボイスチャンネルに参加しています')


@client.tree.command()
async def leave(interaction: Interaction):
    if interaction.guild.id in cfg.in_voice:
        vc = cfg.in_voice[interaction.guild.id]
        await vc.disconnect()
        await interaction.response.send_message('ボイスチャンネルから切断しました')
        del cfg.in_voice[interaction.guild.id]
        del cfg.call_channel[interaction.guild.id]

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.guild and message.guild.id in cfg.in_voice and message.content and not message.content.startswith('!'):
        if cfg.call_channel[message.guild.id] != message.channel:
            return
        vc = cfg.in_voice[message.guild.id]
        # 音声ファイル名に使用できない要素を削除し25文字以内に切り詰め
        clean_message = re.sub(r'[\n\s\\/:*?"<>|]+','',message.content)[:25]
        # ユーザーのメンションを検出
        mention_user = re.findall(r'<@\S{1,}>', message.content)
        mention_user = sorted(set(mention_user), key=mention_user.index)

        speaker_text = message.content

        # メンションをユーザー名に置換
        if len(message.mentions) != 0:
            for mention in message.mentions:
                index = matchindex(mention_user,mention.id)
                if(index != None):
                    if(mention.nick != None):
                        speaker_text = speaker_text.replace(mention_user[index], mention.nick+"さん")
                    elif(mention.global_name != None):
                        speaker_text = speaker_text.replace(mention_user[index], mention.global_name+"さん")
                    else:
                        speaker_text = speaker_text.replace(mention_user[index], mention.name+"さん")

        speaker_text = re.sub(r'<\S{1,}>', '',  speaker_text)
        speaker_text = re.sub(r'\n', ' ',  speaker_text)
        # ファイルの種類と数をカウント
        if len(message.attachments) != 0:
            attach_count = {}
            for i in range(len(message.attachments)):
                print(message.attachments[i].url)
                print(message.attachments[0].content_type)
                if "image" in message.attachments[i].content_type:
                    attach_count["image"] = attach_count.get("image",0) + 1
                elif "video" in message.attachments[i].content_type:
                    attach_count["video"] = attach_count.get("video",0) + 1
                elif "audio" in message.attachments[i].content_type:
                    attach_count["audio"] = attach_count.get("audio",0) + 1
                else:
                    attach_count["other"] = attach_count.get("other",0) + 1

            if(attach_count.get("image",None) != None):
                speaker_text = str(attach_count["image"])+"件の画像ファイル "+speaker_text
            if(attach_count.get("video",None) != None):
                speaker_text = str(attach_count["video"])+"件の動画ファイル "+speaker_text
            if(attach_count.get("audio",None) != None):
                speaker_text = str(attach_count["audio"])+"件の音声ファイル "+speaker_text
            if(attach_count.get("other",None) != None):
                speaker_text = str(attach_count["other"])+"件のファイル "+speaker_text

        # リンク数をカウントし、リンクは削除する
        linkcount = len(re.findall(cfg.url_regex, speaker_text))
        if(linkcount != 0):
            speaker_text = re.sub(cfg.url_regex,'',speaker_text)
            speaker_text = str(linkcount)+"件のリンク "+speaker_text

        # api->genvoice 音声を生成
        if(str(message.guild.id) in user_conf):
            if(str(message.author.id)+"-id" in user_conf[str(message.guild.id)]):
                voice = api.genvoice(speaker_text,user_conf[str(message.guild.id)][str(message.author.id)+"-chara"],user_conf[str(message.guild.id)][str(message.author.id)+"-id"])
            else:
                voice = api.genvoice(speaker_text)
        else:
            voice = api.genvoice(speaker_text)
        temp_file = rf'temp_{clean_message}.wav'

        # 生成した音声を一時ファイルに保存
        with open(temp_file, 'wb') as f:
            f.write(voice)
        # TODO: 発声中にVCから切断された場合にファイルが削除されない
        vc.play(FFmpegPCMAudio(temp_file, executable=cfg.ffmpeg_path), after=lambda e: os.remove(temp_file))


@client.event
async def on_voice_state_update(member, before, after):
    # VC内のユーザーがいなくなった場合に切断
    if member.guild.id in cfg.in_voice and not member == client.user:
        if len(member.guild.voice_client.channel.members) == 1:
            vc = cfg.in_voice[member.guild.id]
            await vc.disconnect()
            del cfg.in_voice[member.guild.id]
            del cfg.call_channel[member.guild.id]

client.run(cfg.token)